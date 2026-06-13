import argparse
import itertools
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.random import default_rng


# ===============================================================
# GLOBALS
# ===============================================================
DEFAULT_BASE_OUTCOMES = ["bp", "cimt", "pvh"]

# Observed covariates (Z_fixed): age/sex/BMI/batch/ancestry PCs
DEFAULT_ZFIX_LABELS = ["age", "sex", "bmi", "batch", "PC1", "PC2"]


def stable_seed(base_seed, tag):
    """Deterministic per-dataset seed so configs don’t accidentally duplicate."""
    h = hashlib.md5(str(tag).encode("utf-8")).hexdigest()
    return int(h[:8], 16) + int(base_seed)


# ===============================================================
# 1) BLOCK ALLOCATION
# ===============================================================
def allocate_blocks(p):
    """
    Allocates blocks: G, Z_fixed, Z_noise, L_treat, L_med, R
    with the rule: R = p//2 (central retinal mediator block)
    and remainder distributed among G, Z, L_treat, L_med.

    Z_fixed represents observed covariates (age/sex/bmi/batch/PCs).
    Z_noise represents latent/unmeasured confounding (environment, measurement bias, unknown factors).
    """
    R = p // 2
    Z_fixed = len(DEFAULT_ZFIX_LABELS)

    if p < 50:
        Z_noise = 0
        G = 1
    elif p < 100:
        Z_noise = 3
        G = 2
    else:
        Z_noise = 6
        G = 4

    remaining = p - (R + Z_fixed + Z_noise + G)

    # Ensure at least 1 Lt and 1 Lm by borrowing from R only for tiny p (not your benchmark case)
    if remaining < 2:
        deficit = 2 - remaining
        R = max(1, R - deficit)
        remaining += deficit

    L_treat = remaining // 2
    L_med = remaining - L_treat

    return dict(
        G=G,
        Z_fixed=Z_fixed,
        Z_noise=Z_noise,
        L_treat=L_treat,
        L_med=L_med,
        R=R,
    )


# ===============================================================
# 2) OUTCOME NAME BUILDER (2^m - 1)
# ===============================================================
def build_outcome_names(base_outcomes):
    cleaned = []
    seen = set()
    for b in base_outcomes:
        s = str(b).strip()
        if not s:
            continue
        if s.startswith("V"):
            s = s[1:]
        if s not in seen:
            cleaned.append(s)
            seen.add(s)

    if len(cleaned) == 0:
        raise ValueError("base_outcomes must contain at least one non-empty outcome name.")

    names = []
    for r in range(1, len(cleaned) + 1):
        for combo in itertools.combinations(cleaned, r):
            names.append("V" + "_".join(combo))

    return names


# ===============================================================
# 3) NODE LIST BUILDER
# ===============================================================
def build_nodes(blocks, V_names):
    names = []
    names += [f"G{i+1}" for i in range(blocks["G"])]

    # Observed covariates
    for i in range(blocks["Z_fixed"]):
        lab = DEFAULT_ZFIX_LABELS[i] if i < len(DEFAULT_ZFIX_LABELS) else f"{i+1}"
        names.append(f"Zfix_{lab}")

    # Latent/unmeasured confounders
    names += [f"Znoise{i+1}" for i in range(blocks["Z_noise"])]

    names += [f"Lt{i+1}" for i in range(blocks["L_treat"])]
    names += [f"Lm{i+1}" for i in range(blocks["L_med"])]
    names += [f"R{i+1}" for i in range(blocks["R"])]
    names += V_names
    return names


def apply_node_name_style(names, node_name_style="canonical", name_tag=None):
    style = str(node_name_style).lower().strip()
    if style == "canonical":
        return list(names)

    if style == "tagged":
        tag = str(name_tag or "").strip()
        if not tag:
            return list(names)
        safe = "".join(ch if ch.isalnum() else "_" for ch in tag)
        safe = safe.strip("_")
        if not safe:
            return list(names)
        return [f"{n}_{safe}" for n in names]

    raise ValueError(f"Unknown node_name_style: {node_name_style}")


# ===============================================================
# 4) RANDOM DAG GENERATORS
# ===============================================================
def random_er_edges(n, k, rng):
    """Erdos-Renyi DAG: edges only i->j with i<j."""
    A = np.zeros((n, n), dtype=int)
    p_edge = min(1.0, k / max(1, n))
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < p_edge:
                A[i, j] = 1
    return A


def random_scale_free_edges(n, k, rng):
    """Simple preferential-attachment DAG over a topological order."""
    A = np.zeros((n, n), dtype=int)
    outdeg = np.zeros(n, dtype=float)
    for j in range(1, n):
        candidates = np.arange(j)
        probs = outdeg[candidates] + 1.0
        probs = probs / probs.sum()
        m = min(j, max(1, int(round(k))))
        parents = rng.choice(candidates, size=m, replace=False, p=probs)
        for i in parents:
            A[int(i), j] = 1
            outdeg[int(i)] += 1
    return A


# ===============================================================
# 5) DOMAIN CAUSAL STRUCTURE MERGE
# ===============================================================
def enforce_domain(
    A,
    names,
    blocks,
    rng,
    domain_edge_prob_min=1.0,
    domain_edge_prob_max=1.0,
    random_fanout_cap=False,
    fanout_min=0,
    fanout_max=999999,
):
    """
    Domain edges:
      G -> L_treat, L_med
      L_treat -> L_med, R*
      L_med -> R*
      R -> V*
      Z* -> L_t*,L_m*,R*,V*

    Forbidden:
      no G->V, no L->V, no Z->G   (Option A keeps G exogenous)
    """
    idx = {n: i for i, n in enumerate(names)}
    Gs = [idx[n] for n in names if n.startswith("G")]
    Zs = [idx[n] for n in names if n.startswith("Zfix") or n.startswith("Znoise")]
    Lts = [idx[n] for n in names if n.startswith("Lt")]
    Lms = [idx[n] for n in names if n.startswith("Lm")]
    Rs = [idx[n] for n in names if n.startswith("R")]
    Vs = [idx[n] for n in names if n.startswith("V")]

    pmin = float(domain_edge_prob_min)
    pmax = float(domain_edge_prob_max)
    if pmin > pmax:
        pmin, pmax = pmax, pmin

    def maybe_add(i, j):
        p = rng.uniform(pmin, pmax)
        if rng.random() < p:
            A[i, j] = 1

    for g in Gs:
        for l in Lts + Lms:
            maybe_add(g, l)

    for lt in Lts:
        for x in Lms + Rs:
            maybe_add(lt, x)

    for lm in Lms:
        for r in Rs:
            maybe_add(lm, r)

    for r in Rs:
        targets = Vs
        if random_fanout_cap:
            cap = int(rng.integers(max(1, fanout_min), max(2, fanout_max + 1)))
            if cap < len(targets):
                targets = list(rng.choice(targets, size=cap, replace=False))
        for v in targets:
            maybe_add(r, v)

    for z in Zs:
        for x in Lts + Lms + Rs + Vs:
            maybe_add(z, x)

    # hard domain constraints
    for g in Gs:
        for v in Vs:
            A[g, v] = 0
    for l in Lts + Lms:
        for v in Vs:
            A[l, v] = 0
    for z in Zs:
        for g in Gs:
            A[z, g] = 0

    return A


def apply_block_permutation(A, names, rng, enabled=False):
    """Optional block permutation while preserving acyclicity by reorienting forward."""
    if not enabled:
        return A, names

    groups = {
        "G": [i for i, x in enumerate(names) if x.startswith("G")],
        "Z": [i for i, x in enumerate(names) if x.startswith("Zfix") or x.startswith("Znoise")],
        "Lt": [i for i, x in enumerate(names) if x.startswith("Lt")],
        "Lm": [i for i, x in enumerate(names) if x.startswith("Lm")],
        "R": [i for i, x in enumerate(names) if x.startswith("R")],
        "V": [i for i, x in enumerate(names) if x.startswith("V")],
    }
    keys = ["G", "Z", "Lt", "Lm", "R", "V"]
    perm_keys = list(rng.permutation(keys))
    order = []
    for k in perm_keys:
        order.extend(groups[k])

    inv = np.zeros(len(names), dtype=int)
    for new_i, old_i in enumerate(order):
        inv[old_i] = new_i

    B = np.zeros_like(A)
    for i in range(A.shape[0]):
        for j in range(A.shape[1]):
            if A[i, j] == 0:
                continue
            ni, nj = inv[i], inv[j]
            if ni < nj:
                B[ni, nj] = 1
            elif nj < ni:
                B[nj, ni] = 1

    new_names = [names[old_i] for old_i in order]
    return B, new_names


# ===============================================================
# 5b) ELL CHAIN ENFORCEMENT (makes ell meaningful)
# ===============================================================
def enforce_ell_chain(A, names, ell, strict=True):
    """
    Force an ell-edge chain from Lt1 to Vbp (first V node).
    If strict=True, prune shortcut edges among (Lt/Lm/R/V) so the shortest
    directed path Lt1->Vbp equals ell.

    ell=2: Lt1 -> R1 -> Vbp
    ell>=3: Lt1 -> Lm1 -> R1 -> R2 -> ... -> Vbp
    """
    idx = {nm: i for i, nm in enumerate(names)}
    Lts = [nm for nm in names if nm.startswith("Lt")]
    Lms = [nm for nm in names if nm.startswith("Lm")]
    Rs = [nm for nm in names if nm.startswith("R")]
    Vs = [nm for nm in names if nm.startswith("V")]

    if not Lts or not Rs or not Vs:
        return A

    ell = int(max(2, ell))

    t = idx[Lts[0]]

    def pick_after(node_names, cur_idx):
        cand = [idx[nm] for nm in node_names if idx[nm] > cur_idx]
        return min(cand) if cand else None

    chain = [t]
    cur = t

    # include Lm1 when ell>=3 if possible
    if ell >= 3 and Lms:
        m = pick_after(Lms, cur)
        if m is None:
            ell = 2
        else:
            chain.append(m)
            cur = m

    # add (ell-2) R steps
    r_steps = ell - 2
    for _ in range(r_steps):
        r = pick_after(Rs, cur)
        if r is None:
            break
        chain.append(r)
        cur = r

    # choose first V after last node; typically Vbp is earliest
    y = pick_after(Vs, cur)
    if y is None:
        return A

    chain.append(y)

    # add edges along chain
    for a, b in zip(chain[:-1], chain[1:]):
        A[a, b] = 1

    if not strict:
        return A

    # ---- strict pruning of shortcuts among Lt/Lm/R/V to make ell meaningful ----
    inv = {i: nm for nm, i in idx.items()}
    chain_names = [inv[i] for i in chain]
    v_target = chain_names[-1]

    lt_i = idx[chain_names[0]]
    next_i = chain[1]

    # prune Lt1 outgoing to (Lm/R/V) except next chain node
    for j, nm in enumerate(names):
        if A[lt_i, j] == 1 and j != next_i and nm.startswith(("Lm", "R", "V")):
            A[lt_i, j] = 0

    # prune Lm1 outgoing to (R/V) except next chain node
    lm_nodes_in_chain = [nm for nm in chain_names if nm.startswith("Lm")]
    if lm_nodes_in_chain:
        lm_i = idx[lm_nodes_in_chain[0]]
        lm_pos = chain_names.index(lm_nodes_in_chain[0])
        lm_next = idx[chain_names[lm_pos + 1]]
        for j, nm in enumerate(names):
            if A[lm_i, j] == 1 and j != lm_next and nm.startswith(("R", "V")):
                A[lm_i, j] = 0

    # prune R nodes:
    # - chain R nodes only point to next chain node (R or V target)
    # - non-chain R nodes cannot point directly to V target (avoid shorter path)
    v_i = idx[v_target]
    for rnm in [nm for nm in names if nm.startswith("R")]:
        ri = idx[rnm]
        if rnm in chain_names:
            pos = chain_names.index(rnm)
            allowed = set()
            if pos + 1 < len(chain_names):
                allowed.add(idx[chain_names[pos + 1]])
            for j, nm in enumerate(names):
                if A[ri, j] == 1 and j not in allowed and nm.startswith(("R", "V")):
                    A[ri, j] = 0
        else:
            if A[ri, v_i] == 1:
                A[ri, v_i] = 0

    # keep Vbp target clean: chain R nodes do not connect to other V outcomes
    chain_r_nodes = [nm for nm in chain_names if nm.startswith("R")]
    all_v = [nm for nm in names if nm.startswith("V")]
    for rnm in chain_r_nodes:
        ri = idx[rnm]
        for vnm in all_v:
            vi = idx[vnm]
            if vi != v_i and A[ri, vi] == 1:
                A[ri, vi] = 0

    return A


# ===============================================================
# 6) NONLINEAR / LINEAR SEM DATA GENERATOR
# ===============================================================
def _draw_edge_weight(rng, weight_dist="normal_pos", min_abs_weight=0.5):
    dist = str(weight_dist).lower().strip()
    m = float(max(1e-9, min_abs_weight))
    if dist == "normal_pos":
        return float(rng.normal(0.6, 0.2))
    if dist == "uniform_gap":
        sign = -1.0 if rng.random() < 0.5 else 1.0
        return float(sign * rng.uniform(m, 2.0))
    if dist == "laplace_gap":
        sign = -1.0 if rng.random() < 0.5 else 1.0
        return float(sign * (m + rng.exponential(scale=0.75)))
    raise ValueError(f"Unknown weight_dist: {weight_dist}")


def generate_sem_data(
    A,
    names,
    n_samples=6000,
    rho_nonlin=0.0,
    noise_scale=1.0,
    seed=None,
    weight_dist="normal_pos",
    min_abs_weight=0.5,
):
    rng = default_rng(seed)
    n = len(names)

    W = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if A[i, j] == 1:
                W[i, j] = _draw_edge_weight(rng, weight_dist=weight_dist, min_abs_weight=min_abs_weight)

    X = np.zeros((n_samples, n))
    topo_order = list(range(n))
    for j in topo_order:
        parents = np.where(A[:, j] == 1)[0]
        if len(parents) == 0:
            X[:, j] = rng.normal(0, 1, size=n_samples)
        else:
            linear_signal = X[:, parents] @ W[parents, j]
            if rho_nonlin > 0:
                nl = np.tanh(linear_signal)
                out = (1 - rho_nonlin) * linear_signal + rho_nonlin * nl
            else:
                out = linear_signal
            X[:, j] = out + rng.normal(0, noise_scale, size=n_samples)

    return pd.DataFrame(X, columns=names), W


def _simulate_intervention(
    A,
    W,
    names,
    n_samples=20000,
    rho_nonlin=0.0,
    noise_scale=1.0,
    seed=1234,
    forced_values=None,
):
    rng = default_rng(seed)
    n = len(names)
    X = np.zeros((n_samples, n), dtype=float)
    forced_values = forced_values or {}
    topo_order = list(range(n))
    for j in topo_order:
        if j in forced_values:
            X[:, j] = float(forced_values[j])
            continue
        parents = np.where(A[:, j] == 1)[0]
        if len(parents) == 0:
            X[:, j] = rng.normal(0.0, noise_scale, size=n_samples)
        else:
            linear_signal = X[:, parents] @ W[parents, j]
            if rho_nonlin > 0:
                nl = np.tanh(linear_signal)
                out = (1 - rho_nonlin) * linear_signal + rho_nonlin * nl
            else:
                out = linear_signal
            X[:, j] = out + rng.normal(0.0, noise_scale, size=n_samples)
    return X


def estimate_ground_truth_effects(
    A,
    W,
    names,
    rho_nonlin=0.0,
    noise_scale=1.0,
    n_mc=20000,
    seed=2026,
    t1=1.0,
    t0=0.0,
):
    idx = {nm: i for i, nm in enumerate(names)}
    lt = [nm for nm in names if nm.startswith("Lt")]
    rr = [nm for nm in names if nm.startswith("R")]
    vv = [nm for nm in names if nm.startswith("V")]
    if not lt or not rr or not vv:
        return {
            "status": "skipped",
            "reason": "required nodes Lt/R/V not present",
            "TE": None,
            "NDE": None,
            "NIE": None,
        }

    t_name, m_name, y_name = lt[0], rr[0], vv[0]
    t_idx, m_idx, y_idx = idx[t_name], idx[m_name], idx[y_name]

    x_t1 = _simulate_intervention(
        A, W, names, n_samples=n_mc, rho_nonlin=rho_nonlin, noise_scale=noise_scale,
        seed=seed + 1, forced_values={t_idx: t1},
    )
    x_t0 = _simulate_intervention(
        A, W, names, n_samples=n_mc, rho_nonlin=rho_nonlin, noise_scale=noise_scale,
        seed=seed + 2, forced_values={t_idx: t0},
    )
    m1 = float(np.mean(x_t1[:, m_idx]))
    m0 = float(np.mean(x_t0[:, m_idx]))

    x_t1_m0 = _simulate_intervention(
        A, W, names, n_samples=n_mc, rho_nonlin=rho_nonlin, noise_scale=noise_scale,
        seed=seed + 3, forced_values={t_idx: t1, m_idx: m0},
    )
    x_t0_m0 = _simulate_intervention(
        A, W, names, n_samples=n_mc, rho_nonlin=rho_nonlin, noise_scale=noise_scale,
        seed=seed + 4, forced_values={t_idx: t0, m_idx: m0},
    )
    x_t0_m1 = _simulate_intervention(
        A, W, names, n_samples=n_mc, rho_nonlin=rho_nonlin, noise_scale=noise_scale,
        seed=seed + 5, forced_values={t_idx: t0, m_idx: m1},
    )

    te = float(np.mean(x_t1[:, y_idx]) - np.mean(x_t0[:, y_idx]))
    nde = float(np.mean(x_t1_m0[:, y_idx]) - np.mean(x_t0_m0[:, y_idx]))
    nie = float(np.mean(x_t0_m1[:, y_idx]) - np.mean(x_t0_m0[:, y_idx]))
    return {
        "status": "ok",
        "treatment": t_name,
        "mediator": m_name,
        "outcome": y_name,
        "t1": float(t1),
        "t0": float(t0),
        "TE": te,
        "NDE": nde,
        "NIE": nie,
        "N_MC": int(n_mc),
    }


# ===============================================================
# 7) MISSINGNESS INJECTION (MCAR / MAR / MIXED)
# ===============================================================
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def inject_missing_values(
    df,
    names,
    rmiss=0.0,
    mechanism="none",
    mar_strength=1.25,
    mar_fraction=0.7,
    seed=None,
):
    mech = str(mechanism).lower().strip()
    if rmiss <= 0 or mech == "none":
        mask = np.zeros(df.shape, dtype=bool)
        return df.copy(), mask, {"mechanism": "none", "target_rmiss": float(rmiss), "realized_rmiss": 0.0}

    if not 0 <= rmiss < 1:
        raise ValueError("rmiss must be in [0,1).")

    rng = default_rng(seed)
    col_to_idx = {c: i for i, c in enumerate(df.columns)}

    # IMPORTANT: keep Z_fixed fully observed (age/sex/bmi/batch/PCs)
    target_cols = [
        c for c in names
        if c.startswith("Znoise")
        or c.startswith("Lt")
        or c.startswith("Lm")
        or c.startswith("R")
        or c.startswith("V")
    ]
    if len(target_cols) == 0:
        target_cols = list(df.columns)
    target_idx = np.array([col_to_idx[c] for c in target_cols], dtype=int)

    mask = np.zeros(df.shape, dtype=bool)

    if mech == "mcar":
        mask[:, target_idx] = rng.random((df.shape[0], len(target_idx))) < rmiss

    elif mech in ("mar", "mixed"):
        ref_cols = [
            c for c in names
            if c.startswith("G")
            or c.startswith("Zfix")
            or c.startswith("Znoise")
            or c.startswith("Lt")
            or c.startswith("Lm")
            or c.startswith("R")
        ]
        ref_idx = [col_to_idx[c] for c in ref_cols if c in col_to_idx]

        if len(ref_idx) == 0:
            mar_mask = rng.random((df.shape[0], len(target_idx))) < rmiss
        else:
            ref = df.iloc[:, ref_idx].to_numpy()
            z = (ref - ref.mean(axis=0, keepdims=True)) / (ref.std(axis=0, keepdims=True) + 1e-8)
            score = z.mean(axis=1)
            score = (score - score.mean()) / (score.std() + 1e-8)

            base_logit = np.log((rmiss + 1e-12) / (1.0 - rmiss + 1e-12))
            p_row = _sigmoid(base_logit + mar_strength * score)
            p_row = np.clip(p_row, 1e-6, 1 - 1e-6)

            mar_mask = rng.random((df.shape[0], len(target_idx))) < p_row[:, None]

        if mech == "mar":
            mask[:, target_idx] = mar_mask
        else:
            mcar_mask = rng.random((df.shape[0], len(target_idx))) < rmiss
            choose_mar = rng.random((df.shape[0], len(target_idx))) < mar_fraction
            mask[:, target_idx] = np.where(choose_mar, mar_mask, mcar_mask)

    else:
        raise ValueError("mechanism must be one of {'none','mcar','mar','mixed'}.")

    df_missing = df.mask(mask)
    realized = float(mask[:, target_idx].mean()) if len(target_idx) > 0 else 0.0
    return df_missing, mask, {
        "mechanism": mech,
        "target_rmiss": float(rmiss),
        "realized_rmiss": realized,
        "num_target_columns": int(len(target_idx)),
    }


# ===============================================================
# 8) MASTER FUNCTION TO GENERATE ONE DATASET
# ===============================================================
def generate_dataset(
    p,
    n,
    rho_nonlin,
    k,
    ell,
    seed=123,
    base_outcomes=None,
    rmiss=0.0,
    missing_mechanism="none",
    mar_strength=1.25,
    mar_fraction=0.7,
    graph_family="er",
    domain_edge_prob_min=1.0,
    domain_edge_prob_max=1.0,
    random_fanout_cap=False,
    fanout_min=1,
    fanout_max=5,
    randomize_block_order=False,
    node_name_style="canonical",
    name_tag=None,
    noise_scale=1.0,
    weight_dist="normal_pos",
    min_abs_weight=0.5,
    estimate_effects=True,
    effect_mc_samples=20000,
):
    if base_outcomes is None:
        base_outcomes = DEFAULT_BASE_OUTCOMES

    V_names = build_outcome_names(base_outcomes)
    blocks = allocate_blocks(p)
    names = build_nodes(blocks, V_names)
    names = apply_node_name_style(names, node_name_style=node_name_style, name_tag=name_tag)

    rng = default_rng(seed)
    family = str(graph_family).lower().strip()
    if family == "scale_free":
        A = random_scale_free_edges(len(names), k, rng)
    else:
        A = random_er_edges(len(names), k, rng)

    A = enforce_domain(
        A,
        names,
        blocks,
        rng,
        domain_edge_prob_min=domain_edge_prob_min,
        domain_edge_prob_max=domain_edge_prob_max,
        random_fanout_cap=random_fanout_cap,
        fanout_min=fanout_min,
        fanout_max=fanout_max,
    )

    A, names = apply_block_permutation(A, names, rng, enabled=randomize_block_order)

    # NEW: make ell meaningful (and avoid duplicates like LowDim-N vs LowDim-D)
    # Note: if randomize_block_order=True, ell enforcement may downgrade if ordering breaks.
    A = enforce_ell_chain(A, names, ell, strict=True)

    df_complete, W = generate_sem_data(
        A,
        names,
        n_samples=n,
        rho_nonlin=rho_nonlin,
        noise_scale=noise_scale,
        seed=seed,
        weight_dist=weight_dist,
        min_abs_weight=min_abs_weight,
    )

    df_missing, missing_mask, missing_meta = inject_missing_values(
        df_complete,
        names,
        rmiss=rmiss,
        mechanism=missing_mechanism,
        mar_strength=mar_strength,
        mar_fraction=mar_fraction,
        seed=seed + 999,
    )

    effects = None
    if estimate_effects:
        effects = estimate_ground_truth_effects(
            A,
            W,
            names,
            rho_nonlin=rho_nonlin,
            noise_scale=noise_scale,
            n_mc=effect_mc_samples,
            seed=seed + 5000,
        )

    return df_missing, df_complete, missing_mask, missing_meta, A, W, names, blocks, V_names, effects


# ===============================================================
# 9) GENERATE ALL 10 CONFIGURATIONS
# ===============================================================
CONFIGS = {
    "LowDim-L": dict(p=20, n=6000, rho=0.0, k=1, ell=3),
    "LowDim-N": dict(p=20, n=6000, rho=0.5, k=1, ell=3),
    "LowDim-P": dict(p=20, n=6000, rho=0.5, k=2, ell=2),
    "LowDim-D": dict(p=20, n=6000, rho=0.5, k=1, ell=6),
    "MidDim-S": dict(p=100, n=6000, rho=0.5, k=1, ell=3),
    "MidDim-D": dict(p=100, n=6000, rho=0.5, k=1, ell=6),
    "HigDim-D": dict(p=200, n=6000, rho=0.5, k=1, ell=3),
    "HigDim-S": dict(p=200, n=6000, rho=0.5, k=1, ell=6),
    "MidDim-P": dict(p=100, n=6000, rho=0.5, k=2, ell=2),
    "MidDim-C": dict(p=50, n=6000, rho=0.5, k=1, ell=6),
}


def generate_all_datasets(
    out_data_dir="synthetic_benchmark_v2/data",
    out_truth_dir="synthetic_benchmark_v2/truth",
    base_outcomes=None,
    rmiss=0.15,
    missing_mechanism="mixed",
    mar_strength=1.25,
    mar_fraction=0.7,
    graph_family="er",
    domain_edge_prob_min=1.0,
    domain_edge_prob_max=1.0,
    random_fanout_cap=False,
    fanout_min=1,
    fanout_max=5,
    randomize_block_order=False,
    node_name_style="canonical",
    noise_scale=1.0,
    weight_dist="normal_pos",
    min_abs_weight=0.5,
    estimate_effects=True,
    effect_mc_samples=20000,
):
    out_data_dir = Path(out_data_dir)
    out_truth_dir = Path(out_truth_dir)
    out_data_dir.mkdir(parents=True, exist_ok=True)
    out_truth_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    if base_outcomes is None:
        base_outcomes = DEFAULT_BASE_OUTCOMES

    for ds_name, params in CONFIGS.items():
        print(f"Generating: {ds_name}")

        seed_ds = stable_seed(123, ds_name)

        (
            df_missing,
            df_complete,
            missing_mask,
            missing_meta,
            A,
            W,
            names,
            blocks,
            V_names,
            effects,
        ) = generate_dataset(
            p=params["p"],
            n=params["n"],
            rho_nonlin=params["rho"],
            k=params["k"],
            ell=params["ell"],
            seed=seed_ds,
            base_outcomes=base_outcomes,
            rmiss=rmiss,
            missing_mechanism=missing_mechanism,
            mar_strength=mar_strength,
            mar_fraction=mar_fraction,
            graph_family=graph_family,
            domain_edge_prob_min=domain_edge_prob_min,
            domain_edge_prob_max=domain_edge_prob_max,
            random_fanout_cap=random_fanout_cap,
            fanout_min=fanout_min,
            fanout_max=fanout_max,
            randomize_block_order=randomize_block_order,
            node_name_style=node_name_style,
            name_tag=ds_name if str(node_name_style).lower().strip() == "tagged" else None,
            noise_scale=noise_scale,
            weight_dist=weight_dist,
            min_abs_weight=min_abs_weight,
            estimate_effects=estimate_effects,
            effect_mc_samples=effect_mc_samples,
        )

        data_ds_dir = out_data_dir / ds_name
        truth_ds_dir = out_truth_dir / ds_name
        data_ds_dir.mkdir(parents=True, exist_ok=True)
        truth_ds_dir.mkdir(parents=True, exist_ok=True)

        df_missing.to_csv(data_ds_dir / f"{ds_name}_data.csv", index=False)
        df_complete.to_csv(data_ds_dir / f"{ds_name}_data_complete.csv", index=False)
        pd.DataFrame(missing_mask.astype(int), columns=names).to_csv(
            data_ds_dir / f"{ds_name}_missing_mask.csv", index=False
        )
        with open(data_ds_dir / f"{ds_name}_nodes.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(names))

        pd.DataFrame(A, index=names, columns=names).to_csv(truth_ds_dir / f"{ds_name}_adjacency.csv")
        pd.DataFrame(W, index=names, columns=names).to_csv(truth_ds_dir / f"{ds_name}_weights.csv")
        if effects is not None:
            with open(truth_ds_dir / f"{ds_name}_effects.json", "w", encoding="utf-8") as f:
                json.dump(effects, f, indent=2)

        manifest.append(
            {
                "dataset": ds_name,
                "seed": int(seed_ds),
                "params": params,
                "blocks": blocks,
                "base_outcomes": list(base_outcomes),
                "num_outcomes": len(V_names),
                "node_name_style": str(node_name_style),
                "missingness": missing_meta,
                "noise_distribution": "Normal(0, noise_scale^2)",
                "noise_scale": float(noise_scale),
                "weight_dist": str(weight_dist),
                "min_abs_weight": float(min_abs_weight),
                "files": {
                    "data": f"{ds_name}/{ds_name}_data.csv",
                    "data_complete": f"{ds_name}/{ds_name}_data_complete.csv",
                    "missing_mask": f"{ds_name}/{ds_name}_missing_mask.csv",
                    "nodes": f"{ds_name}/{ds_name}_nodes.txt",
                },
            }
        )

    with open(out_data_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("All datasets generated.")
    print(f"Data output:  {out_data_dir.resolve()}")
    print(f"Truth output: {out_truth_dir.resolve()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate synthetic benchmark datasets with separate data/truth outputs.")
    ap.add_argument("--out-data-dir", default="synthetic_benchmark_v2/data")
    ap.add_argument("--out-truth-dir", default="synthetic_benchmark_v2/truth")
    ap.add_argument("--rmiss", type=float, default=0.15)
    ap.add_argument("--missing-mechanism", default="mixed", choices=["none", "mcar", "mar", "mixed"])
    ap.add_argument("--mar-strength", type=float, default=1.25)
    ap.add_argument("--mar-fraction", type=float, default=0.7)

    ap.add_argument("--graph-family", default="er", choices=["er", "scale_free"])
    ap.add_argument("--domain-edge-prob-min", type=float, default=1.0)
    ap.add_argument("--domain-edge-prob-max", type=float, default=1.0)
    ap.add_argument("--random-fanout-cap", action="store_true")
    ap.add_argument("--fanout-min", type=int, default=1)
    ap.add_argument("--fanout-max", type=int, default=5)
    ap.add_argument("--randomize-block-order", action="store_true")
    ap.add_argument("--node-name-style", default="canonical", choices=["canonical", "tagged"])
    ap.add_argument("--noise-scale", type=float, default=1.0, help="Gaussian noise std; default gives eps~N(0,1)")
    ap.add_argument("--weight-dist", default="normal_pos", choices=["normal_pos", "uniform_gap", "laplace_gap"])
    ap.add_argument("--min-abs-weight", type=float, default=0.5, help="Lower abs bound used by gap-style weight dists.")
    ap.add_argument("--no-estimate-effects", action="store_true", help="Disable Monte Carlo TE/NDE/NIE estimation.")
    ap.add_argument("--effect-mc-samples", type=int, default=20000)

    args = ap.parse_args()

    generate_all_datasets(
        out_data_dir=args.out_data_dir,
        out_truth_dir=args.out_truth_dir,
        rmiss=args.rmiss,
        missing_mechanism=args.missing_mechanism,
        mar_strength=args.mar_strength,
        mar_fraction=args.mar_fraction,
        graph_family=args.graph_family,
        domain_edge_prob_min=args.domain_edge_prob_min,
        domain_edge_prob_max=args.domain_edge_prob_max,
        random_fanout_cap=args.random_fanout_cap,
        fanout_min=args.fanout_min,
        fanout_max=args.fanout_max,
        randomize_block_order=args.randomize_block_order,
        node_name_style=args.node_name_style,
        noise_scale=args.noise_scale,
        weight_dist=args.weight_dist,
        min_abs_weight=args.min_abs_weight,
        estimate_effects=not bool(args.no_estimate_effects),
        effect_mc_samples=args.effect_mc_samples,
    )