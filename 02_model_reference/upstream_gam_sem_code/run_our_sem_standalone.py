#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd

from anti_leak import (
    assert_no_truth_loaded,
    configure_truth_dirs,
    evaluation_phase,
    guarded_open,
    guarded_read_csv,
    training_phase,
)


def choose_threshold(W_hat, strategy="quantile", q=0.35):
    vals = np.abs(W_hat[np.nonzero(W_hat)])
    if vals.size == 0:
        return 0.0
    if strategy == "nonzero":
        return 0.0
    if strategy == "quantile":
        return float(np.quantile(vals, q))
    if strategy == "mean":
        return float(vals.mean())
    if strategy == "median":
        return float(np.median(vals))
    raise ValueError(f"Unknown threshold strategy: {strategy}")


def binarize_from_weights(W_hat, th, strategy="quantile"):
    if strategy == "nonzero":
        A = (np.abs(W_hat) > 0).astype(int)
    else:
        A = (np.abs(W_hat) >= th).astype(int)
    np.fill_diagonal(A, 0)
    return A


def _undirected_set(edges):
    return set(tuple(sorted(e)) for e in edges)


def edges_from_adj(A):
    return [(i, j) for i in range(A.shape[0]) for j in range(A.shape[1]) if A[i, j] != 0]


def adjacency_f1(A_ref, A_pred):
    t = _undirected_set(edges_from_adj(A_ref))
    p = _undirected_set(edges_from_adj(A_pred))
    tp = len(t & p)
    fp = len(p - t)
    fn = len(t - p)
    prec = tp / (tp + fp + 1e-12)
    rec = tp / (tp + fn + 1e-12)
    return 2 * prec * rec / (prec + rec + 1e-12)


def orientation_f1(A_ref, A_pred):
    t = set(edges_from_adj(A_ref))
    p = set(edges_from_adj(A_pred))
    tp = len(t & p)
    fp = len(p - t)
    fn = len(t - p)
    prec = tp / (tp + fp + 1e-12)
    rec = tp / (tp + fn + 1e-12)
    return 2 * prec * rec / (prec + rec + 1e-12)


def shd(A_ref, A_pred):
    sk_t = ((A_ref + A_ref.T) > 0).astype(int)
    sk_p = ((A_pred + A_pred.T) > 0).astype(int)
    sk_diff = int(np.sum(np.abs(sk_t - sk_p)) // 2)
    orient = 0
    n = A_ref.shape[0]
    common = sk_t & sk_p
    for i in range(n):
        for j in range(n):
            if i == j or not common[i, j]:
                continue
            if A_ref[i, j] != A_pred[i, j]:
                orient += 1
    return sk_diff + orient


def normalized_shd(A_ref, A_pred):
    return shd(A_ref, A_pred) / max(1, int(np.sum((A_ref + A_ref.T) > 0) // 2))


def causal_accuracy(A_ref, A_pred):
    denom = A_ref.shape[0] * (A_ref.shape[0] - 1)
    return 1.0 - (np.sum(np.abs(A_ref - A_pred)) / max(1, denom))


def edge_prf(A_ref, A_pred, directed=True):
    if directed:
        t = set(edges_from_adj(A_ref))
        p = set(edges_from_adj(A_pred))
    else:
        t = _undirected_set(edges_from_adj(A_ref))
        p = _undirected_set(edges_from_adj(A_pred))
    tp = len(t & p)
    fp = len(p - t)
    fn = len(t - p)
    prec = tp / (tp + fp + 1e-12)
    rec = tp / (tp + fn + 1e-12)
    f1 = 2 * prec * rec / (prec + rec + 1e-12)
    return prec, rec, f1


def _signed_log1p_df(df):
    x = df.values.astype(float)
    xt = np.sign(x) * np.log1p(np.abs(x))
    return pd.DataFrame(xt, columns=df.columns, index=df.index)


def _to_float(x, default=np.nan):
    try:
        return float(x)
    except Exception:
        return float(default)


def _extract_sem_fit_stats(model_obj):
    out = {}
    try:
        import semopy
        stats_obj = semopy.calc_stats(model_obj)
    except Exception:
        return out
    if stats_obj is None:
        return out
    keymap = {
        "CFI": "sem_cfi",
        "TLI": "sem_tli",
        "RMSEA": "sem_rmsea",
        "SRMR": "sem_srmr",
        "AIC": "sem_aic",
        "BIC": "sem_bic",
        "chi2": "sem_chi2",
        "DoF": "sem_dof",
        "dof": "sem_dof",
        "p-value": "sem_pvalue",
    }
    try:
        if isinstance(stats_obj, pd.DataFrame) and len(stats_obj) > 0:
            row = stats_obj.iloc[0]
            for k, outk in keymap.items():
                if k in row.index:
                    v = _to_float(row[k], default=np.nan)
                    if np.isfinite(v):
                        out[outk] = v
        elif isinstance(stats_obj, dict):
            for k, outk in keymap.items():
                if k in stats_obj:
                    v = _to_float(stats_obj.get(k), default=np.nan)
                    if np.isfinite(v):
                        out[outk] = v
    except Exception:
        return out
    return out


def _extract_sem_solver_info(model_obj):
    out = {}
    lr = getattr(model_obj, "last_result", None)
    if lr is None:
        return out
    succ = getattr(lr, "success", None)
    if succ is not None:
        out["sem_converged"] = bool(succ)
    nit = getattr(lr, "n_it", None)
    if nit is not None:
        try:
            out["sem_n_iter"] = int(nit)
        except Exception:
            pass
    fun = getattr(lr, "fun", None)
    if fun is not None:
        try:
            fv = float(fun)
            if np.isfinite(fv):
                out["sem_obj"] = fv
        except Exception:
            pass
    return out


def _sem_fit_flags(fit_stats):
    rmsea = fit_stats.get("sem_rmsea")
    cfi = fit_stats.get("sem_cfi")
    tli = fit_stats.get("sem_tli")
    srmr = fit_stats.get("sem_srmr")
    flags = {
        "fit_pass_rmsea_lt_0p08": bool(rmsea is not None and rmsea < 0.08),
        "fit_pass_cfi_gt_0p90": bool(cfi is not None and cfi > 0.90),
        "fit_pass_tli_gt_0p90": bool(tli is not None and tli > 0.90),
        "fit_pass_srmr_lt_0p08": bool(srmr is not None and srmr < 0.08),
    }
    flags["fit_pass_all"] = all(flags.values()) if flags else False
    return flags


def _obs_lines_from_pairs(obs_pairs):
    by_child = {}
    for child, parent in obs_pairs:
        by_child.setdefault(child, []).append(parent)
    lines = []
    for child in sorted(by_child.keys()):
        pars = sorted(set(by_child[child]))
        if pars:
            lines.append(f"{child} ~ " + " + ".join(pars))
    return lines


def _fit_gam_like_equation(df_model, child, pars, alpha=0.01, spline_df=5):
    """
    Initial GAM-style additive equation fit.

    This stage uses smooth basis expansion per parent and aggregates the fitted
    basis coefficients back to one edge weight per parent. It keeps the SEM
    graph extraction simple while introducing nonlinear additive structure.
    """
    try:
        import patsy
        import statsmodels.api as sm
    except Exception as e:
        raise RuntimeError(f"GAM dependencies unavailable: {e}")

    if not pars:
        return {}

    term_chunks = [f"bs({p}, df={int(spline_df)}, degree=3, include_intercept=False)" for p in pars]
    formula = f"{child} ~ " + " + ".join(term_chunks)
    y, x = patsy.dmatrices(formula, data=df_model, return_type="dataframe")
    fit = sm.OLS(y, x).fit()

    parent_weights = {}
    for p in pars:
        pref = f"bs({p},"
        term_cols = [c for c in x.columns if c.startswith(pref)]
        if not term_cols:
            continue
        sig = []
        for c in term_cols:
            pval = _to_float(fit.pvalues.get(c, np.nan), default=np.nan)
            coef = abs(_to_float(fit.params.get(c, 0.0), default=0.0))
            if np.isfinite(pval) and pval < alpha and coef > 1e-8:
                sig.append(coef)
        if sig:
            parent_weights[p] = float(max(sig))
    return parent_weights


def run_our_sem_model(df, alpha=0.01, variant="domain_latent", x_transform="log1p_signed"):
    cols = list(df.columns)
    idx = {c: i for i, c in enumerate(cols)}

    g = [c for c in cols if c.startswith(("G", "g"))]
    z = [c for c in cols if c.startswith("Zfix") or c.startswith("Znoise")]
    lt = [c for c in cols if c.startswith("Lt")]
    lm = [c for c in cols if c.startswith("Lm")]
    l = lt + lm
    r = [c for c in cols if c.startswith("R")]
    v = [c for c in cols if c.startswith("V")]

    vname = str(variant).lower().strip()
    xname = str(x_transform).lower().strip()
    df_model = _signed_log1p_df(df) if xname == "log1p_signed" else df

    equations = []
    if vname in ("truth_aligned", "domain_structured", "domain_structured_gam", "gam_sem"):
        for x in lt:
            pars = z + g
            if pars:
                equations.append((x, pars))
        for x in lm:
            pars = z + g + lt
            if pars:
                equations.append((x, pars))
        for x in r:
            pars = z + lt + lm
            if pars:
                equations.append((x, pars))
    else:
        for x in l:
            pars = z + g
            if pars:
                equations.append((x, pars))
        for x in r:
            pars = z + g + l
            if pars:
                equations.append((x, pars))
    for x in v:
        pars = z + r
        if pars:
            equations.append((x, pars))

    if not equations:
        return None, "No SEM equations generated from domain structure.", {}

    if vname in ("domain_structured_gam", "gam_sem"):
        try:
            w_hat = np.zeros((len(cols), len(cols)), dtype=float)
            for child, pars in equations:
                parent_weights = _fit_gam_like_equation(
                    df_model=df_model,
                    child=child,
                    pars=pars,
                    alpha=alpha,
                    spline_df=5,
                )
                for parent, weight in parent_weights.items():
                    if parent in idx and child in idx:
                        w_hat[idx[parent], idx[child]] = max(w_hat[idx[parent], idx[child]], float(weight))
            return w_hat, None, {
                "backend": "gam_additive_ols",
                "our_sem_variant": vname,
                "our_sem_transform": xname,
            }
        except Exception as e:
            return None, f"GAM-SEM failed: {e}", {}

    if vname == "domain_latent":
        try:
            import semopy
            latent_blocks = {
                "G_lat": g,
                "Z_lat": z,
                "Lt_lat": lt,
                "Lm_lat": lm,
                "R_lat": r,
                "V_lat": v,
            }
            latent_struct = [
                ("Lt_lat", ["Z_lat", "G_lat"]),
                ("Lm_lat", ["Z_lat", "G_lat", "Lt_lat"]),
                ("R_lat", ["Z_lat", "Lt_lat", "Lm_lat"]),
                ("V_lat", ["Z_lat", "R_lat"]),
            ]
            latent_lines = []
            active_latents = set()
            indicator_to_latent = {}
            for lat, inds in latent_blocks.items():
                if not inds:
                    continue
                active_latents.add(lat)
                if len(inds) == 1:
                    ind = inds[0]
                    latent_lines.append(f"{lat} =~ 1*{ind}")
                    latent_lines.append(f"{ind} ~~ 0*{ind}")
                    indicator_to_latent[ind] = lat
                else:
                    latent_lines.append(f"{lat} =~ " + " + ".join(inds))
                    for ind in inds:
                        indicator_to_latent[ind] = lat

            struct_lines = []
            for child, pars in latent_struct:
                if child not in active_latents:
                    continue
                use_pars = [p for p in pars if p in active_latents]
                if use_pars:
                    struct_lines.append(f"{child} ~ " + " + ".join(use_pars))

            observed_pairs = []
            for lhs, rhs in equations:
                for parent in rhs:
                    observed_pairs.append((str(lhs), str(parent)))
            observed_pairs = sorted(set(observed_pairs))
            if not latent_lines or not struct_lines or not observed_pairs:
                return None, "Domain-latent SEM lacks identifiable latent or observed structure.", {}

            best = None
            best_rmsea = np.inf
            current_pairs = list(observed_pairs)
            for _ in range(4):
                obs_lines = _obs_lines_from_pairs(current_pairs)
                if not obs_lines:
                    break
                model = semopy.Model("\n".join(latent_lines + struct_lines + obs_lines))
                model.fit(df_model)
                est = model.inspect()
                fit_stats = _extract_sem_fit_stats(model)
                solver_info = _extract_sem_solver_info(model)
                rmsea = float(fit_stats.get("sem_rmsea", np.inf))
                if not np.isfinite(rmsea):
                    rmsea = np.inf
                if best is None or rmsea < best_rmsea or (
                    abs(rmsea - best_rmsea) <= 1e-12 and len(current_pairs) < len(best["pairs"])
                ):
                    best = {
                        "model": model,
                        "est": est,
                        "fit_stats": dict(fit_stats),
                        "solver_info": dict(solver_info),
                        "pairs": list(current_pairs),
                    }
                    best_rmsea = rmsea

                cur_set = set(current_pairs)
                keep = set()
                for _, row in est.iterrows():
                    if str(row.get("op")) != "~":
                        continue
                    child = str(row.get("lval"))
                    parent = str(row.get("rval"))
                    if (child, parent) not in cur_set:
                        continue
                    p = _to_float(row.get("p-value", np.nan))
                    b = abs(_to_float(row.get("Estimate", 0.0), default=0.0))
                    if (not np.isfinite(p) or p < alpha) and b > 1e-8:
                        keep.add((child, parent))
                if not keep or len(keep) == len(cur_set):
                    break
                current_pairs = sorted(keep)

            if best is None:
                return None, "Domain-latent SEM fitting failed.", {}

            est = best["est"]
            fit_stats = best["fit_stats"]
            solver_info = best["solver_info"]

            loadings = {}
            for _, row in est.iterrows():
                if str(row.get("op")) != "~":
                    continue
                lval = str(row.get("lval"))
                rval = str(row.get("rval"))
                if lval in indicator_to_latent and rval in active_latents:
                    if indicator_to_latent[lval] != rval:
                        continue
                    p = _to_float(row.get("p-value", np.nan))
                    if np.isfinite(p) and p >= alpha:
                        continue
                    loadings[(rval, lval)] = _to_float(row.get("Estimate", 1.0), default=1.0)
            for ind, lat in indicator_to_latent.items():
                loadings.setdefault((lat, ind), 1.0)

            latent_edges = []
            for _, row in est.iterrows():
                if str(row.get("op")) != "~":
                    continue
                child = str(row.get("lval"))
                parent = str(row.get("rval"))
                if child in active_latents and parent in active_latents:
                    p = _to_float(row.get("p-value", np.nan))
                    if np.isfinite(p) and p >= alpha:
                        continue
                    latent_edges.append((parent, child, _to_float(row.get("Estimate", 0.0), default=0.0)))
            if not latent_edges:
                return None, "Domain-latent SEM found no significant latent paths.", {}

            w_lat = np.zeros((len(cols), len(cols)), dtype=float)
            for p_lat, c_lat, b in latent_edges:
                for p_ind in latent_blocks.get(p_lat, []):
                    lp = float(abs(loadings.get((p_lat, p_ind), 1.0)))
                    for c_ind in latent_blocks.get(c_lat, []):
                        lc = float(abs(loadings.get((c_lat, c_ind), 1.0)))
                        if p_ind in idx and c_ind in idx:
                            w_lat[idx[p_ind], idx[c_ind]] = max(
                                w_lat[idx[p_ind], idx[c_ind]],
                                float(abs(b) * lp * lc),
                            )

            w_obs = np.zeros((len(cols), len(cols)), dtype=float)
            for _, row in est.iterrows():
                if str(row.get("op")) != "~":
                    continue
                child = str(row.get("lval"))
                parent = str(row.get("rval"))
                if parent in idx and child in idx:
                    p = _to_float(row.get("p-value", np.nan))
                    if np.isfinite(p) and p >= alpha:
                        continue
                    w_obs[idx[parent], idx[child]] = max(
                        w_obs[idx[parent], idx[child]],
                        abs(_to_float(row.get("Estimate", 0.0), default=0.0)),
                    )

            w_hat = np.maximum(w_lat, w_obs)
            meta = {
                "backend": "semopy_domain_latent_hybrid",
                "our_sem_variant": vname,
                "our_sem_transform": xname,
                "latent_edges": int(len(latent_edges)),
                "obs_edges_nonzero": int(np.sum(w_obs > 0)),
                "obs_pairs_specified": int(len(best["pairs"])),
            }
            meta.update(fit_stats)
            meta.update(solver_info)
            meta.update(_sem_fit_flags(fit_stats))
            return w_hat, None, meta
        except Exception as e:
            return None, f"Domain-latent SEM failed: {e}", {}

    try:
        import statsmodels.api as sm

        w_hat = np.zeros((len(cols), len(cols)), dtype=float)
        for child, pars in equations:
            y = df_model[child].values.astype(float)
            x = df_model[pars].values.astype(float)
            x = sm.add_constant(x, has_constant="add")
            fit = sm.OLS(y, x).fit()
            pvals = fit.pvalues[1:]
            coefs = fit.params[1:]
            for i, p in enumerate(pvals):
                if np.isfinite(p) and float(p) < alpha:
                    w_hat[idx[pars[i]], idx[child]] = float(abs(coefs[i]))
        return w_hat, None, {
            "backend": "statsmodels_ols_domain_sem",
            "our_sem_variant": vname,
            "our_sem_transform": xname,
        }
    except Exception as e:
        return None, f"OLS SEM fallback failed: {e}", {}


def impute_data(df, strategy="auto", random_state=123):
    if strategy == "none":
        return df.copy(), {"imputation": "none", "imputer_backend": "none"}

    imp_strategy = strategy
    if strategy == "auto":
        imp_strategy = "iterative" if df.shape[1] <= 120 else "median"

    if imp_strategy in ("mean", "median", "most_frequent"):
        from sklearn.impute import SimpleImputer

        imp = SimpleImputer(strategy=imp_strategy)
        arr = imp.fit_transform(df.values.astype(float))
        return pd.DataFrame(arr, columns=df.columns, index=df.index), {
            "imputation": imp_strategy,
            "imputer_backend": "sklearn.SimpleImputer",
        }

    if imp_strategy == "knn":
        from sklearn.impute import KNNImputer

        imp = KNNImputer(n_neighbors=5)
        arr = imp.fit_transform(df.values.astype(float))
        return pd.DataFrame(arr, columns=df.columns, index=df.index), {
            "imputation": "knn",
            "imputer_backend": "sklearn.KNNImputer",
        }

    if imp_strategy == "iterative":
        from sklearn.experimental import enable_iterative_imputer  # noqa: F401
        from sklearn.impute import IterativeImputer

        imp = IterativeImputer(random_state=random_state, max_iter=20, sample_posterior=False)
        arr = imp.fit_transform(df.values.astype(float))
        return pd.DataFrame(arr, columns=df.columns, index=df.index), {
            "imputation": "iterative",
            "imputer_backend": "sklearn.IterativeImputer",
        }

    raise ValueError(f"Unknown imputation strategy: {strategy}")


def _resolve_data_truth_roots(root, data_root=None, truth_root=None):
    if data_root and truth_root:
        return data_root, truth_root
    rp = Path(root)
    # Preferred clean layout in this release: dataset/data + dataset/truth
    cand_data = rp / "dataset" / "data"
    cand_truth = rp / "dataset" / "truth"
    if cand_data.exists() and cand_truth.exists():
        return str(cand_data), str(cand_truth)
    # Backward-compatible fallback
    cand_data = rp / "data"
    cand_truth = rp / "truth"
    if cand_data.exists() and cand_truth.exists():
        return str(cand_data), str(cand_truth)
    return data_root or root, truth_root or root


def load_training_data(data_root, scenario, use_complete=False):
    ddir = Path(data_root) / scenario
    if not ddir.is_dir():
        raise FileNotFoundError(f"Scenario folder not found: {ddir}")
    data_fp = ddir / (f"{scenario}_data_complete.csv" if use_complete else f"{scenario}_data.csv")
    if use_complete and not data_fp.exists():
        data_fp = ddir / f"{scenario}_data.csv"
    if not data_fp.exists():
        raise FileNotFoundError(str(data_fp))

    nodes_fp = ddir / f"{scenario}_nodes.txt"
    miss_fp = ddir / f"{scenario}_missing_mask.csv"

    df = guarded_read_csv(data_fp)
    nodes = list(df.columns)
    if nodes_fp.exists():
        with guarded_open(nodes_fp, "r", encoding="utf-8") as f:
            nodes = [ln.strip() for ln in f if ln.strip()]
    if len(nodes) == len(df.columns):
        df = df.copy()
        df.columns = nodes
    meta = {
        "input_file": data_fp.name,
        "input_missing_rate": float(df.isna().mean().mean()),
        "input_missing_cells": int(df.isna().sum().sum()),
    }
    if miss_fp.exists():
        mm = guarded_read_csv(miss_fp)
        meta["missing_mask_shape"] = list(mm.shape)
    return df, nodes, meta


def discover_scenarios(data_root):
    out = []
    for d in sorted(os.listdir(data_root)):
        ddir = Path(data_root) / d
        if ddir.is_dir() and (ddir / f"{d}_data.csv").exists():
            out.append(d)
    return out


def evaluate_with_truth(scenario, truth_root, data_root, w_hat, threshold_strategy, threshold_q, runtime_sec, imp_meta, missing_meta, meta):
    with evaluation_phase():
        truth_dir = Path(truth_root) / scenario
        adj_fp = truth_dir / f"{scenario}_adjacency.csv"
        if not adj_fp.exists():
            raise FileNotFoundError(str(adj_fp))
        a_ref = guarded_read_csv(adj_fp, header=0, index_col=0).values

    th = choose_threshold(w_hat, strategy=threshold_strategy, q=threshold_q)
    a_pred = binarize_from_weights(w_hat, th, strategy=threshold_strategy)
    shd_raw = shd(a_ref, a_pred)
    sk_prec, sk_rec, sk_f1 = edge_prf(a_ref, a_pred, directed=False)
    dir_prec, dir_rec, dir_f1 = edge_prf(a_ref, a_pred, directed=True)
    row = {
        "scenario": scenario,
        "method": "RetiSEM",
        "status": "ok",
        "error": "none",
        "SHD": normalized_shd(a_ref, a_pred),
        "SHD_raw": int(shd_raw),
        "causal_accuracy": causal_accuracy(a_ref, a_pred),
        "Adjacency_F1": adjacency_f1(a_ref, a_pred),
        "Orientation_F1": orientation_f1(a_ref, a_pred),
        "skeleton_precision": sk_prec,
        "skeleton_recall": sk_rec,
        "skeleton_F1": sk_f1,
        "directed_precision": dir_prec,
        "directed_recall": dir_rec,
        "directed_F1": dir_f1,
        "num_pred_edges": int(a_pred.sum()),
        "num_true_edges": int(a_ref.sum()),
        "threshold_strategy": threshold_strategy,
        "threshold_q": float(threshold_q),
        "threshold_value": float(th),
        "runtime_sec": float(runtime_sec),
        "imputation": imp_meta.get("imputation"),
        "imputer_backend": imp_meta.get("imputer_backend"),
        "missing_before": missing_meta.get("input_missing_rate", np.nan),
        "missing_after": 0.0,
    }
    for k, v in (meta or {}).items():
        if k not in row:
            row[k] = v

    out_dir = Path(data_root).parent / "_tmp_unused"
    _ = out_dir  # keep linter silent for parity with no-truth path
    return row, a_pred, a_ref


def run_one_scenario(args, data_root, truth_root, scenario):
    with training_phase():
        df, nodes, missing_meta = load_training_data(data_root, scenario, use_complete=args.use_complete_data)
        assert_no_truth_loaded(stage=f"before_our_sem_fit_{scenario}")
        df_used, imp_meta = impute_data(df, strategy=args.impute, random_state=args.seed)
        if float(df_used.isna().mean().mean()) > 0:
            raise RuntimeError("Imputation left missing values.")
        t0 = time.time()
        w_hat, err, meta = run_our_sem_model(
            df=df_used,
            alpha=args.alpha,
            variant=args.our_sem_variant,
            x_transform=args.our_sem_transform,
        )
        runtime_sec = time.time() - t0
        assert_no_truth_loaded(stage=f"after_our_sem_fit_{scenario}")

    out_dir = Path(args.out) / scenario
    out_dir.mkdir(parents=True, exist_ok=True)

    if w_hat is None:
        row = {
            "scenario": scenario,
            "method": "RetiSEM",
            "status": "error",
            "error": str(err),
            "runtime_sec": float(runtime_sec),
            "threshold_strategy": args.threshold_strategy,
            "threshold_q": float(args.threshold_q),
            "imputation": imp_meta.get("imputation"),
            "imputer_backend": imp_meta.get("imputer_backend"),
            "missing_before": missing_meta.get("input_missing_rate", np.nan),
            "missing_after": float(df_used.isna().mean().mean()),
        }
        row.update(meta or {})
        pd.DataFrame([row]).to_csv(out_dir / "metrics.csv", index=False)
        with open(out_dir / "run_diagnostics.json", "w", encoding="utf-8") as f:
            json.dump({"scenario": scenario, "error": err, "meta": meta}, f, indent=2)
        return row

    np.savetxt(out_dir / "weights_hat.csv", w_hat, delimiter=",")

    adj_path = Path(truth_root) / scenario / f"{scenario}_adjacency.csv"
    if adj_path.exists():
        row, a_pred, a_ref = evaluate_with_truth(
            scenario=scenario,
            truth_root=truth_root,
            data_root=data_root,
            w_hat=w_hat,
            threshold_strategy=args.threshold_strategy,
            threshold_q=args.threshold_q,
            runtime_sec=runtime_sec,
            imp_meta=imp_meta,
            missing_meta=missing_meta,
            meta=meta,
        )
        pd.DataFrame(a_pred, index=nodes, columns=nodes).to_csv(out_dir / "adjacency_pred.csv")
        pd.DataFrame(a_ref, index=nodes, columns=nodes).to_csv(out_dir / "adjacency_truth.csv")
    else:
        th = choose_threshold(w_hat, strategy=args.threshold_strategy, q=args.threshold_q)
        a_pred = binarize_from_weights(w_hat, th, strategy=args.threshold_strategy)
        row = {
            "scenario": scenario,
            "method": "RetiSEM",
            "status": "ok_no_truth",
            "error": "none",
            "runtime_sec": float(runtime_sec),
            "threshold_strategy": args.threshold_strategy,
            "threshold_q": float(args.threshold_q),
            "threshold_value": float(th),
            "num_pred_edges": int(a_pred.sum()),
            "imputation": imp_meta.get("imputation"),
            "imputer_backend": imp_meta.get("imputer_backend"),
            "missing_before": missing_meta.get("input_missing_rate", np.nan),
            "missing_after": 0.0,
        }
        for k, v in (meta or {}).items():
            if k not in row:
                row[k] = v
        pd.DataFrame(a_pred, index=nodes, columns=nodes).to_csv(out_dir / "adjacency_pred.csv")

    pd.DataFrame([row]).to_csv(out_dir / "metrics.csv", index=False)
    with open(out_dir / "run_diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "scenario": scenario,
                "data_root": str(Path(data_root).resolve()),
                "truth_root": str(Path(truth_root).resolve()),
                "method": "RetiSEM",
                "our_sem_variant": args.our_sem_variant,
                "our_sem_transform": args.our_sem_transform,
                "threshold_strategy": args.threshold_strategy,
                "threshold_q": float(args.threshold_q),
                "impute": args.impute,
                "meta": meta,
            },
            f,
            indent=2,
        )
    return row


def main():
    ap = argparse.ArgumentParser(description="Standalone domain-specific GAM-SEM benchmark runner (anti-leak safe).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--data_root", default=None)
    ap.add_argument("--truth_root", default=None)
    ap.add_argument("--scenario", default="all")
    ap.add_argument("--out", default="results_our_sem_standalone")
    ap.add_argument("--impute", default="auto", choices=["auto", "none", "mean", "median", "most_frequent", "knn", "iterative"])
    ap.add_argument("--use_complete_data", action="store_true")
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--threshold_strategy", default="quantile", choices=["quantile", "mean", "median", "nonzero"])
    ap.add_argument("--threshold_q", type=float, default=0.35)
    ap.add_argument(
        "--our_sem_variant",
        default="domain_structured_gam",
        choices=["base", "truth_aligned", "domain_structured", "domain_latent", "domain_structured_gam", "gam_sem"],
    )
    ap.add_argument("--our_sem_transform", default="none", choices=["none", "log1p_signed"])
    ap.add_argument("--seed", type=int, default=123)
    args = ap.parse_args()

    data_root, truth_root = _resolve_data_truth_roots(args.root, args.data_root, args.truth_root)
    configure_truth_dirs(truth_root)
    scenarios = discover_scenarios(data_root) if args.scenario == "all" else [args.scenario]
    if not scenarios:
        raise RuntimeError(f"No scenarios found under data root: {data_root}")

    print(
        f"[CONFIG] data_root={Path(data_root).resolve()} truth_root={Path(truth_root).resolve()} "
        f"variant={args.our_sem_variant} transform={args.our_sem_transform} q={args.threshold_q}"
    )

    rows = []
    for sc in scenarios:
        print(f"\n=== Running scenario {sc} ===")
        rows.append(run_one_scenario(args, data_root, truth_root, sc))

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    combined = pd.DataFrame(rows).fillna(0)
    combined_fp = out_root / "combined_metrics.csv"
    combined.to_csv(combined_fp, index=False)
    print(f"\nCombined metrics: {combined_fp}")


if __name__ == "__main__":
    main()


