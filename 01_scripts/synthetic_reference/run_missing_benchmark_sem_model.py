#!/usr/bin/env python3
"""
Clean benchmark runner for the GAM-SEM stage.

Scope:
- Methods: PC, LINGAM, DAGMA, NOTEARS, DECI, RetiSEM
- Strict anti-leak split:
  - training phase reads only data
  - evaluation phase reads truth for metrics

This script is intentionally minimal and avoids legacy/unused method branches.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
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
from run_our_sem_standalone import run_our_sem_model


# ------------------------------
# Metrics and threshold helpers
# ------------------------------
def choose_threshold(w_hat: np.ndarray, strategy: str = "quantile", q: float = 0.35) -> float:
    vals = np.abs(w_hat[np.nonzero(w_hat)])
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


def binarize_from_weights(w_hat: np.ndarray, th: float, strategy: str = "quantile") -> np.ndarray:
    if strategy == "nonzero":
        a = (np.abs(w_hat) > 0).astype(int)
    else:
        a = (np.abs(w_hat) >= th).astype(int)
    np.fill_diagonal(a, 0)
    return a


def edges_from_adj(a: np.ndarray):
    return [(i, j) for i in range(a.shape[0]) for j in range(a.shape[1]) if a[i, j] != 0]


def _undirected_set(edges):
    return set(tuple(sorted(e)) for e in edges)


def adjacency_f1(a_ref: np.ndarray, a_pred: np.ndarray) -> float:
    t = _undirected_set(edges_from_adj(a_ref))
    p = _undirected_set(edges_from_adj(a_pred))
    tp = len(t & p)
    fp = len(p - t)
    fn = len(t - p)
    prec = tp / (tp + fp + 1e-12)
    rec = tp / (tp + fn + 1e-12)
    return 2 * prec * rec / (prec + rec + 1e-12)


def orientation_f1(a_ref: np.ndarray, a_pred: np.ndarray) -> float:
    t = set(edges_from_adj(a_ref))
    p = set(edges_from_adj(a_pred))
    tp = len(t & p)
    fp = len(p - t)
    fn = len(t - p)
    prec = tp / (tp + fp + 1e-12)
    rec = tp / (tp + fn + 1e-12)
    return 2 * prec * rec / (prec + rec + 1e-12)


def shd(a_ref: np.ndarray, a_pred: np.ndarray) -> int:
    sk_t = ((a_ref + a_ref.T) > 0).astype(int)
    sk_p = ((a_pred + a_pred.T) > 0).astype(int)
    sk_diff = int(np.sum(np.abs(sk_t - sk_p)) // 2)
    orient = 0
    n = a_ref.shape[0]
    common = sk_t & sk_p
    for i in range(n):
        for j in range(n):
            if i == j or not common[i, j]:
                continue
            if a_ref[i, j] != a_pred[i, j]:
                orient += 1
    return sk_diff + orient


def normalized_shd(a_ref: np.ndarray, a_pred: np.ndarray) -> float:
    n = int(a_ref.shape[0])
    return float(shd(a_ref, a_pred) / max(1, n * (n - 1)))


def edge_prf(a_ref: np.ndarray, a_pred: np.ndarray, directed: bool = True):
    if directed:
        t = set(edges_from_adj(a_ref))
        p = set(edges_from_adj(a_pred))
    else:
        t = _undirected_set(edges_from_adj(a_ref))
        p = _undirected_set(edges_from_adj(a_pred))
    tp = len(t & p)
    fp = len(p - t)
    fn = len(t - p)
    prec = tp / (tp + fp + 1e-12)
    rec = tp / (tp + fn + 1e-12)
    f1 = 2 * prec * rec / (prec + rec + 1e-12)
    return prec, rec, f1


def causal_accuracy(a_ref: np.ndarray, a_pred: np.ndarray) -> float:
    denom = a_ref.shape[0] * (a_ref.shape[0] - 1)
    return 1.0 - (np.sum(np.abs(a_ref - a_pred)) / max(1, denom))


# ------------------------------
# Data and imputation
# ------------------------------
def _resolve_data_truth_roots(root: str, data_root: str | None = None, truth_root: str | None = None):
    if data_root and truth_root:
        return data_root, truth_root
    rp = Path(root)
    # Preferred clean layout in this release: dataset/data + dataset/truth
    cand_data = rp / "dataset" / "data"
    cand_truth = rp / "dataset" / "truth"
    if cand_data.exists() and cand_truth.exists():
        return str(cand_data), str(cand_truth)
    # Backward-compatible fallback: data + truth directly under root
    cand_data = rp / "data"
    cand_truth = rp / "truth"
    if cand_data.exists() and cand_truth.exists():
        return str(cand_data), str(cand_truth)
    return data_root or root, truth_root or root


def discover_scenarios(data_root: str):
    out = []
    for d in sorted(os.listdir(data_root)):
        ddir = Path(data_root) / d
        if ddir.is_dir() and (ddir / f"{d}_data.csv").exists():
            out.append(d)
    return out


def load_training_data(data_root: str, scenario: str, use_complete: bool = False):
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


def _impute_mean(df: pd.DataFrame) -> pd.DataFrame:
    return df.fillna(df.mean(numeric_only=True))


def _impute_median(df: pd.DataFrame) -> pd.DataFrame:
    return df.fillna(df.median(numeric_only=True))


def _impute_most_frequent(df: pd.DataFrame) -> pd.DataFrame:
    fill_map = {}
    for c in df.columns:
        mode = df[c].mode(dropna=True)
        fill_map[c] = mode.iloc[0] if len(mode) else 0.0
    return df.fillna(fill_map)


def impute_data(df: pd.DataFrame, strategy: str = "auto", random_state: int = 123):
    strat = (strategy or "auto").lower()
    if strat == "none":
        if df.isna().any().any():
            raise ValueError("Missing values present with --impute none.")
        return df.copy(), {"imputation": "none", "imputer_backend": None}

    if not df.isna().any().any():
        return df.copy(), {"imputation": "none_needed", "imputer_backend": None}

    if strat == "auto":
        for candidate in ("iterative", "knn", "median"):
            try:
                out, meta = impute_data(df, strategy=candidate, random_state=random_state)
                meta["imputation"] = f"auto->{candidate}"
                return out, meta
            except Exception:
                continue
        raise RuntimeError("Auto imputation failed for all strategies.")

    if strat in ("mean", "median", "most_frequent"):
        if strat == "mean":
            out = _impute_mean(df)
        elif strat == "median":
            out = _impute_median(df)
        else:
            out = _impute_most_frequent(df)
        if out.isna().any().any():
            out = out.fillna(0.0)
        return out, {"imputation": strat, "imputer_backend": "pandas_fillna"}

    if strat == "knn":
        from sklearn.impute import KNNImputer

        imp = KNNImputer(n_neighbors=5)
        arr = imp.fit_transform(df.values.astype(float))
        return pd.DataFrame(arr, columns=df.columns, index=df.index), {
            "imputation": "knn",
            "imputer_backend": "sklearn.KNNImputer",
        }

    if strat == "iterative":
        from sklearn.experimental import enable_iterative_imputer  # noqa: F401
        from sklearn.impute import IterativeImputer

        imp = IterativeImputer(random_state=random_state, max_iter=20, sample_posterior=False)
        arr = imp.fit_transform(df.values.astype(float))
        return pd.DataFrame(arr, columns=df.columns, index=df.index), {
            "imputation": "iterative",
            "imputer_backend": "sklearn.IterativeImputer",
        }

    raise ValueError(f"Unknown imputation strategy: {strategy}")


# ------------------------------
# Method implementations
# ------------------------------
def _causallearn_graph_to_adj(graph, n: int):
    mat = np.asarray(graph.graph)
    a = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if mat[i, j] == -1 and mat[j, i] == 1:
                a[i, j] = 1.0
    return a


def run_pc(df: pd.DataFrame, alpha: float = 0.01):
    try:
        from causallearn.search.ConstraintBased.PC import pc
        from causallearn.utils.cit import fisherz
    except Exception as e:
        return None, f"PC not available: {e}", {}

    x = df.values.astype(float)
    try:
        cg = pc(x, alpha=alpha, indep_test=fisherz, stable=True)
    except TypeError:
        cg = pc(x, alpha=alpha, indep_test_func=fisherz, stable=True)
    a = _causallearn_graph_to_adj(cg.G, x.shape[1]).astype(float)
    return a, None, {}


def run_lingam(df: pd.DataFrame):
    x = df.values.astype(float)
    try:
        from lingam import DirectLiNGAM

        model = DirectLiNGAM()
        model.fit(x)
        return np.asarray(model.adjacency_matrix_, dtype=float), None, {}
    except Exception as e:
        return None, f"LiNGAM failed: {e}", {}


def run_dagma(df: pd.DataFrame):
    x = df.values.astype(float)
    try:
        from dagma.linear import DagmaLinear

        model = DagmaLinear(loss_type="l2", verbose=False)
        w = model.fit(x, lambda1=0.03, w_threshold=0.0)
        return np.asarray(w, dtype=float), None, {}
    except Exception as e:
        return None, f"DAGMA failed: {e}", {}


def run_notears(df: pd.DataFrame):
    x = df.values.astype(float)
    # Some environments hard-abort on OpenMP/Torch init; allow explicit safe fallback.
    if os.environ.get("FORCE_NOTEARS_DAGMA_FALLBACK", "").strip().lower() in ("1", "true", "yes", "on"):
        w, err, meta = run_dagma(df)
        if w is not None:
            meta = dict(meta or {})
            meta["backend"] = "dagma_fallback_for_notears"
            meta["fallback_reason"] = "FORCE_NOTEARS_DAGMA_FALLBACK enabled"
            return w, None, meta
        return None, f"NOTEARS forced DAGMA fallback failed: {err}", {}

    try:
        from castle.algorithms import Notears

        model = Notears()
        model.learn(x)
        a = getattr(model, "causal_matrix", None)
        if a is None:
            a = getattr(model, "adjacency_matrix", None)
        if a is None:
            raise RuntimeError("gCastle NOTEARS did not expose adjacency.")
        return np.asarray(a, dtype=float), None, {"backend": "gcastle_notears"}
    except Exception as e1:
        last_err = f"gCastle NOTEARS failed: {e1}"

    try:
        import torch
        import notears_pytorch

        x_t = torch.from_numpy(x.astype(np.float32))
        try:
            w = notears_pytorch.notears_linear(x_t, max_iter=1000, lr=1e-2, lambda1=0.01, lambda2=0.01)
        except TypeError:
            model = notears_pytorch.NotearsModel(d=x.shape[1])
            w = model.fit(x_t, max_iter=1000, lr=1e-2, lambda1=0.01, lambda2=0.01)
        if hasattr(w, "detach"):
            w = w.detach().cpu().numpy()
        return np.asarray(w, dtype=float), None, {"backend": "notears_pytorch"}
    except Exception as e2:
        last_err = f"{last_err}; notears-pytorch failed: {e2}"

    w, err, meta = run_dagma(df)
    if w is not None:
        meta = dict(meta or {})
        meta["backend"] = "dagma_fallback_for_notears"
        meta["fallback_reason"] = last_err
        return w, None, meta
    return None, f"NOTEARS failed: {last_err}; DAGMA fallback failed: {err}", {}


def _write_deci_variables_json(df: pd.DataFrame, fp: Path):
    variables = []
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        lo = float(np.nanmin(s.values)) if np.isfinite(np.nanmin(s.values)) else -1.0
        hi = float(np.nanmax(s.values)) if np.isfinite(np.nanmax(s.values)) else 1.0
        if lo == hi:
            lo, hi = lo - 1.0, hi + 1.0
        variables.append(
            {
                "name": str(c),
                "query": True,
                "target": False,
                "type": "continuous",
                "lower": lo,
                "upper": hi,
                "always_observed": True,
            }
        )
    fp.write_text(json.dumps({"variables": variables}, indent=2), encoding="utf-8")


def run_deci(df: pd.DataFrame):
    if os.environ.get("FORCE_DECI_DAGMA_FALLBACK", "").strip().lower() in ("1", "true", "yes", "on"):
        w, err, meta = run_dagma(df)
        if w is not None:
            meta = dict(meta or {})
            meta["backend"] = "dagma_fallback_for_deci"
            meta["fallback_reason"] = "FORCE_DECI_DAGMA_FALLBACK enabled"
            return w, None, meta
        return None, f"DECI forced DAGMA fallback failed: {err}", {}

    codex_root = Path(__file__).resolve().parents[3]
    causica_root = codex_root / "deps" / "causica-main"
    causica_src = causica_root / "src"

    try:
        if causica_src.exists() and str(causica_src) not in sys.path:
            sys.path.insert(0, str(causica_src))
        from causica.lightning.modules.deci_module import DECIModule  # type: ignore
        import torch  # type: ignore
    except Exception as e:
        w, err, meta = run_dagma(df)
        if w is not None:
            meta = dict(meta or {})
            meta["backend"] = "dagma_fallback_for_deci"
            meta["fallback_reason"] = f"DECI import failed: {e}"
            return w, None, meta
        return None, f"DECI import failed: {e}; DAGMA fallback failed: {err}", {}

    try:
        cfg_dir = causica_src / "causica" / "config" / "lightning"
        model_tpl = cfg_dir / "default_gaussian.yaml"
        if not model_tpl.exists():
            raise FileNotFoundError(f"Missing DECI model template: {model_tpl}")

        work = Path(tempfile.mkdtemp(prefix="deci_quick_"))
        data_root = work / "data" / "sigma_quick"
        out_ckpt_dir = work / "outputs"
        data_root.mkdir(parents=True, exist_ok=True)
        out_ckpt_dir.mkdir(parents=True, exist_ok=True)

        n = len(df)
        idx = np.arange(n)
        rng = np.random.default_rng(1337)
        rng.shuffle(idx)
        n_train = max(10, int(0.7 * n))
        train_df = df.iloc[idx[:n_train]].reset_index(drop=True)
        test_df = df.iloc[idx[n_train:]].reset_index(drop=True)

        train_df.to_csv(data_root / "train.csv", index=False, header=False)
        test_df.to_csv(data_root / "test.csv", index=False, header=False)
        _write_deci_variables_json(train_df, data_root / "variables.json")
        train_df.to_csv(work / "train.csv", index=False, header=False)
        test_df.to_csv(work / "test.csv", index=False, header=False)
        _write_deci_variables_json(train_df, work / "variables.json")

        data_cfg = cfg_dir / "sigma_quick_data_codex.yaml"
        model_cfg = cfg_dir / "sigma_quick_model_codex.yaml"

        data_text = "\n".join(
            [
                "class_path: causica.lightning.data_modules.variable_spec_data.VariableSpecDataModule",
                "init_args:",
                f"  root_path: {work.as_posix()}",
                "  dataset_name: sigma_quick",
                "  batch_size: 128",
                "  standardize: true",
                "  load_interventional: false",
                "  load_counterfactual: false",
                "  load_validation: false",
            ]
        )
        model_text = model_tpl.read_text(encoding="utf-8")
        model_text = model_text.replace('dirpath: "./outputs"', f'dirpath: "{out_ckpt_dir.as_posix()}"')
        model_text = model_text.replace("max_epochs: 2000", "max_epochs: 3")

        data_cfg.write_text(data_text, encoding="utf-8")
        model_cfg.write_text(model_text, encoding="utf-8")

        cmd = [sys.executable, "-m", "causica.lightning.main", "--config", str(model_cfg), "--data", str(data_cfg)]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(causica_src)
        subprocess.run(
            cmd,
            cwd=str(causica_root),
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=600,
        )

        ckpt = out_ckpt_dir / "best_model.ckpt"
        if not ckpt.exists():
            ckpt = out_ckpt_dir / "last.ckpt"
        if not ckpt.exists():
            raise FileNotFoundError(f"DECI ckpt missing in {out_ckpt_dir}")

        module = DECIModule.load_from_checkpoint(str(ckpt), map_location="cpu")
        module.setup()
        module.eval()
        n_vars = df.shape[1]
        with torch.no_grad():
            sems = module.sem_module().sample(torch.Size([20]))
            vote = np.zeros((n_vars, n_vars), dtype=float)
            for s in sems:
                g = s.graph.detach().cpu().numpy()
                vote += np.abs(g)

        w_hat = vote / 20.0
        return w_hat, None, {"backend": "causica_deci_lightning_quick"}
    except Exception as e:
        w, err, meta = run_dagma(df)
        if w is not None:
            meta = dict(meta or {})
            meta["backend"] = "dagma_fallback_for_deci"
            meta["fallback_reason"] = f"DECI train/score failed: {e}"
            return w, None, meta
        return None, f"DECI failed: {e}; DAGMA fallback failed: {err}", {}


def run_method(method: str, df: pd.DataFrame, args):
    m = method.upper()
    try:
        if m == "PC":
            return run_pc(df, alpha=args.alpha)
        if m == "LINGAM":
            return run_lingam(df)
        if m == "DAGMA":
            return run_dagma(df)
        if m == "NOTEARS":
            return run_notears(df)
        if m == "DECI":
            return run_deci(df)
        if m in ("RETISEM", "OUR_SEM_MODEL", "OURS_SEM", "SEM_MODEL"):
            return run_our_sem_model(
                df=df,
                alpha=args.alpha,
                variant=args.our_sem_variant,
                x_transform=args.our_sem_transform,
            )
        return None, f"Unknown method: {method}", {}
    except MemoryError:
        return None, f"{method} failed: MemoryError", {"backend": "runtime_guard", "fallback_reason": "memory_error"}
    except Exception as e:
        return None, f"{method} failed: {e}", {"backend": "runtime_guard", "fallback_reason": type(e).__name__}


# ------------------------------
# Scenario execution
# ------------------------------
def evaluate_method(
    scenario: str,
    method: str,
    nodes,
    w_hat: np.ndarray,
    truth_root: str,
    threshold_strategy: str,
    threshold_q: float,
    runtime_sec: float,
    imp_meta: dict,
    missing_meta: dict,
    method_meta: dict,
):
    with evaluation_phase():
        truth_dir = Path(truth_root) / scenario
        adj_fp = truth_dir / f"{scenario}_adjacency.csv"
        if not adj_fp.exists():
            th = choose_threshold(w_hat, strategy=threshold_strategy, q=threshold_q)
            a_pred = binarize_from_weights(w_hat, th, strategy=threshold_strategy)
            row = {
                "scenario": scenario,
                "method": method,
                "status": "ok_no_truth",
                "error": "none",
                "runtime_sec": float(runtime_sec),
                "threshold_strategy": threshold_strategy,
                "threshold_q": float(threshold_q),
                "threshold_value": float(th),
                "num_pred_edges": int(a_pred.sum()),
                "imputation": imp_meta.get("imputation"),
                "imputer_backend": imp_meta.get("imputer_backend"),
                "missing_before": missing_meta.get("input_missing_rate", np.nan),
                "missing_after": 0.0,
            }
            row.update(method_meta or {})
            return row, a_pred, None

        a_ref = guarded_read_csv(adj_fp, header=0, index_col=0).values

    th = choose_threshold(w_hat, strategy=threshold_strategy, q=threshold_q)
    a_pred = binarize_from_weights(w_hat, th, strategy=threshold_strategy)
    shd_raw = shd(a_ref, a_pred)
    sk_prec, sk_rec, sk_f1 = edge_prf(a_ref, a_pred, directed=False)
    dir_prec, dir_rec, dir_f1 = edge_prf(a_ref, a_pred, directed=True)
    row = {
        "scenario": scenario,
        "method": method,
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
    row.update(method_meta or {})
    return row, a_pred, a_ref


def run_one_scenario(args, data_root: str, truth_root: str, scenario: str):
    out_dir = Path(args.out) / scenario
    out_dir.mkdir(parents=True, exist_ok=True)

    # Training phase only: load, impute, fit methods.
    with training_phase():
        df, nodes, missing_meta = load_training_data(data_root, scenario, use_complete=args.use_complete_data)
        assert_no_truth_loaded(stage=f"before_fit_{scenario}")
        df_used, imp_meta = impute_data(df, strategy=args.impute, random_state=args.seed)
        if float(df_used.isna().mean().mean()) > 0:
            raise RuntimeError("Imputation left missing values.")

        fit_out = []
        for m in args.methods:
            t0 = time.time()
            w_hat, err, meta = run_method(m, df_used, args)
            runtime_sec = time.time() - t0
            fit_out.append((m, w_hat, err, meta or {}, runtime_sec))
            assert_no_truth_loaded(stage=f"after_fit_{scenario}_{m}")

    rows = []
    diag = {
        "scenario": scenario,
        "data_root": str(Path(data_root).resolve()),
        "truth_root": str(Path(truth_root).resolve()),
        "methods": list(args.methods),
        "threshold_strategy": args.threshold_strategy,
        "threshold_q": float(args.threshold_q),
        "impute": args.impute,
        "alpha": float(args.alpha),
        "our_sem_variant": args.our_sem_variant,
        "our_sem_transform": args.our_sem_transform,
        "errors": {},
    }

    for method, w_hat, err, meta, runtime_sec in fit_out:
        mdir = out_dir / method
        mdir.mkdir(parents=True, exist_ok=True)

        if w_hat is None:
            row = {
                "scenario": scenario,
                "method": method,
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
            rows.append(row)
            diag["errors"][method] = str(err)
            continue

        w_hat = np.asarray(w_hat, dtype=float)
        pd.DataFrame(w_hat, index=nodes, columns=nodes).to_csv(mdir / "weights_hat.csv")

        row, a_pred, a_ref = evaluate_method(
            scenario=scenario,
            method=method,
            nodes=nodes,
            w_hat=w_hat,
            truth_root=truth_root,
            threshold_strategy=args.threshold_strategy,
            threshold_q=args.threshold_q,
            runtime_sec=runtime_sec,
            imp_meta=imp_meta,
            missing_meta=missing_meta,
            method_meta=meta,
        )
        pd.DataFrame(a_pred, index=nodes, columns=nodes).to_csv(mdir / "adjacency_pred.csv")
        if a_ref is not None:
            pd.DataFrame(a_ref, index=nodes, columns=nodes).to_csv(mdir / "adjacency_truth.csv")

        rows.append(row)

    pd.DataFrame(rows).to_csv(out_dir / "metrics.csv", index=False)
    with open(out_dir / "run_diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(diag, f, indent=2)
    return rows


def main():
    ap = argparse.ArgumentParser(description="GAM-SEM missing-data benchmark with strict anti-leak split.")
    ap.add_argument("--root", default=".", help="Root containing dataset/data and dataset/truth (preferred).")
    ap.add_argument("--data_root", default=None, help="Explicit data root override")
    ap.add_argument("--truth_root", default=None, help="Explicit truth root override")
    ap.add_argument("--scenario", default="all", help="Scenario id (e.g., LowDim-N) or 'all'")
    ap.add_argument(
        "--methods",
        nargs="+",
        default=["PC", "LINGAM", "DAGMA", "NOTEARS", "DECI", "RetiSEM"],
    )
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument(
        "--impute",
        default="auto",
        choices=["auto", "none", "mean", "median", "most_frequent", "knn", "iterative"],
    )
    ap.add_argument("--use_complete_data", action="store_true")
    ap.add_argument("--out", default="results")
    ap.add_argument("--threshold_strategy", default="quantile", choices=["quantile", "mean", "median", "nonzero"])
    ap.add_argument("--threshold_q", type=float, default=0.35)
    ap.add_argument(
        "--our_sem_variant",
        default="domain_structured_gam",
        choices=["base", "truth_aligned", "domain_structured", "domain_latent", "domain_structured_gam", "gam_sem"],
    )
    ap.add_argument("--our_sem_transform", default="none", choices=["none", "log1p_signed"])
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--use_domain_priors", action="store_true", help="Accepted for compatibility.")
    args = ap.parse_args()

    data_root, truth_root = _resolve_data_truth_roots(args.root, args.data_root, args.truth_root)
    configure_truth_dirs(truth_root)

    scenarios = discover_scenarios(data_root) if args.scenario == "all" else [args.scenario]
    if not scenarios:
        raise RuntimeError(f"No scenarios found under data root: {data_root}")

    print(
        f"[CONFIG] data_root={Path(data_root).resolve()} truth_root={Path(truth_root).resolve()} "
        f"methods={args.methods} q={args.threshold_q} impute={args.impute} "
        f"our_sem_variant={args.our_sem_variant} transform={args.our_sem_transform}"
    )

    all_rows = []
    for sc in scenarios:
        print(f"\n=== Running scenario {sc} ===")
        all_rows.extend(run_one_scenario(args, data_root, truth_root, sc))

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    combined_fp = out_root / "combined_metrics.csv"
    pd.DataFrame(all_rows).fillna(0).to_csv(combined_fp, index=False)
    print(f"\nCombined metrics: {combined_fp}")


if __name__ == "__main__":
    main()

