#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import SplineTransformer, StandardScaler


SUPPORTED_MODELS = [
    "linear",
    "RetiSEM_GAM",
]

DEFAULT_Z_COVARS = ["DMDHRAGE", "RIAGENDR", "RIDRETH1", "DMDEDUC3"]
DEFAULT_G_COVARS = ["GREF_AMR", "GREF_EUR", "GREF_SAS", "GREF_entropy"]
DEFAULT_WEIGHT_COL_CANDIDATES = ["WTMEC2YR", "WTSAF2YR"]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run the final release mediation workflow on real data.")
    ap.add_argument("--input-csv", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--bootstrap", type=int, default=50)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--min-complete-rows", type=int, default=300)
    ap.add_argument("--contrast-q-low", type=float, default=0.25)
    ap.add_argument("--contrast-q-high", type=float, default=0.75)
    ap.add_argument("--exposures", nargs="+", required=True)
    ap.add_argument("--mediators", nargs="+", required=True)
    ap.add_argument("--outcomes", nargs="+", required=True)
    ap.add_argument("--covars", nargs="+", required=True)
    ap.add_argument("--z-covars", nargs="+", default=None)
    ap.add_argument("--g-covars", nargs="+", default=None)
    ap.add_argument("--weight-col", default=None)
    ap.add_argument("--gam-n-knots", type=int, default=6)
    ap.add_argument("--gam-degree", type=int, default=3)
    ap.add_argument("--gam-transform", default="none", choices=["none", "log1p_signed"])
    ap.add_argument("--models", nargs="+", default=["linear", "RetiSEM_GAM"])
    return ap.parse_args()


def ci_excludes_zero(lo: float, hi: float) -> bool:
    if np.isnan(lo) or np.isnan(hi):
        return False
    return (lo > 0 and hi > 0) or (lo < 0 and hi < 0)


def safe_quantile_pair(series: pd.Series, q_low: float, q_high: float) -> tuple[float, float]:
    if isinstance(series, pd.DataFrame):
        if series.shape[1] == 1:
            series = series.iloc[:, 0]
        else:
            series = series.iloc[:, 0]
    x0 = float(series.quantile(q_low))
    x1 = float(series.quantile(q_high))
    if np.isfinite(x0) and np.isfinite(x1) and abs(x1 - x0) > 1e-12:
        return x0, x1
    vals = series.to_numpy(dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return 0.0, 1.0
    x0 = float(np.nanmin(vals))
    x1 = float(np.nanmax(vals))
    if abs(x1 - x0) > 1e-12:
        return x0, x1
    return float(x0), float(x0 + 1.0)


def _set_constant(df: pd.DataFrame, col: str, value: float) -> pd.DataFrame:
    out = df.copy()
    out[col] = float(value)
    return out


def _set_column(df: pd.DataFrame, col: str, values: np.ndarray) -> pd.DataFrame:
    out = df.copy()
    out[col] = np.asarray(values, dtype=float)
    return out


def _signed_log1p_array(x: np.ndarray) -> np.ndarray:
    return np.sign(x) * np.log1p(np.abs(x))


def _normalize_covariate_arg(values: list[str] | None, default_values: list[str]) -> list[str]:
    if values is None:
        return list(default_values)
    if len(values) == 1 and str(values[0]).strip().lower() in {"none", "null", "empty"}:
        return []
    return list(values)


def resolve_covariate_blocks(df: pd.DataFrame, args: argparse.Namespace) -> tuple[list[str], list[str], list[str]]:
    cols = set(df.columns)
    z_covars = [c for c in _normalize_covariate_arg(args.z_covars, DEFAULT_Z_COVARS) if c in cols]
    g_covars = [c for c in _normalize_covariate_arg(args.g_covars, DEFAULT_G_COVARS) if c in cols]
    flat_covars = [c for c in args.covars if c in cols]

    if flat_covars:
        seen = set(z_covars) | set(g_covars)
        for c in flat_covars:
            if c not in seen:
                z_covars.append(c)
                seen.add(c)

    covars = z_covars + [c for c in g_covars if c not in z_covars]
    return covars, z_covars, g_covars


def resolve_weight_col(df: pd.DataFrame, args: argparse.Namespace) -> str | None:
    if args.weight_col and args.weight_col in df.columns:
        return args.weight_col
    for c in DEFAULT_WEIGHT_COL_CANDIDATES:
        if c in df.columns:
            return c
    return None


def fit_linear_model(formula: str, data: pd.DataFrame, weight_col: str | None):
    if weight_col and weight_col in data.columns:
        return smf.wls(formula, data=data, weights=data[weight_col]).fit()
    return smf.ols(formula, data=data).fit()


class GAMAdditiveRidgeCVModel:
    def __init__(self, seed: int, n_knots: int = 6, degree: int = 3, x_transform: str = "none"):
        self.seed = seed
        self.n_knots = n_knots
        self.degree = degree
        self.x_transform = x_transform
        self.columns: list[str] = []
        self.transformers: dict[str, SplineTransformer] = {}
        self.scaler = StandardScaler()
        self.model = RidgeCV(alphas=np.asarray([0.01, 0.1, 1.0, 10.0, 100.0], dtype=float))

    def _transform(self, x: pd.DataFrame, fit: bool) -> np.ndarray:
        blocks = []
        if fit:
            self.columns = list(x.columns)
            self.transformers = {}
        for col in self.columns:
            arr = x[[col]].to_numpy(dtype=float)
            if self.x_transform == "log1p_signed":
                arr = _signed_log1p_array(arr)
            if fit:
                tf = SplineTransformer(
                    n_knots=self.n_knots,
                    degree=self.degree,
                    include_bias=False,
                )
                block = tf.fit_transform(arr)
                self.transformers[col] = tf
            else:
                block = self.transformers[col].transform(arr)
            blocks.append(block)
        if not blocks:
            return np.zeros((len(x), 0), dtype=float)
        return np.concatenate(blocks, axis=1)

    def fit(self, x: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None):
        xt = self._transform(x, fit=True)
        if sample_weight is not None and "sample_weight" in inspect.signature(self.scaler.fit).parameters:
            xs = self.scaler.fit_transform(xt, sample_weight=np.asarray(sample_weight, dtype=float))
        else:
            xs = self.scaler.fit_transform(xt)
        if sample_weight is not None and "sample_weight" in inspect.signature(self.model.fit).parameters:
            self.model.fit(xs, y.to_numpy(dtype=float), sample_weight=np.asarray(sample_weight, dtype=float))
        else:
            self.model.fit(xs, y.to_numpy(dtype=float))
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        xt = self._transform(x[self.columns], fit=False)
        xs = self.scaler.transform(xt)
        return np.asarray(self.model.predict(xs), dtype=float)


def make_nonlinear_model(model_type: str, seed: int, args: argparse.Namespace | None = None):
    if model_type == "RetiSEM_GAM":
        return GAMAdditiveRidgeCVModel(
            seed=seed,
            n_knots=int(args.gam_n_knots) if args is not None else 6,
            degree=int(args.gam_degree) if args is not None else 3,
            x_transform=str(args.gam_transform) if args is not None else "none",
        )
    raise ValueError(f"Unsupported model type: {model_type}")


def fit_nonlinear_model(
    x: pd.DataFrame,
    y: pd.Series,
    seed: int,
    model_type: str,
    sample_weight: pd.Series | None,
    args: argparse.Namespace | None,
):
    model = make_nonlinear_model(model_type, seed, args=args)
    if sample_weight is not None and "sample_weight" in inspect.signature(model.fit).parameters:
        model.fit(x, y, sample_weight=np.asarray(sample_weight, dtype=float))
    else:
        model.fit(x, y)
    return model


def _predict_linear(model, pred_df: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict(pred_df), dtype=float)


def _predict_nonlinear(model, pred_df: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict(pred_df), dtype=float)


def fit_models(
    d: pd.DataFrame,
    exposure: str,
    mediators: list[str],
    outcome: str,
    covars: list[str],
    model_type: str,
    seed: int,
    weight_col: str | None,
    args: argparse.Namespace | None,
):
    covars_used = [c for c in covars if c in d.columns]
    med_list = [m for m in mediators if m in d.columns]
    sample_weight = d[weight_col] if weight_col and weight_col in d.columns else None
    if model_type == "linear":
        cov_expr = " + ".join(covars_used) if covars_used else ""
        total_formula = f"{outcome} ~ {exposure}" + (f" + {cov_expr}" if cov_expr else "")
        outcome_formula = f"{outcome} ~ {exposure} + {' + '.join(med_list)}" + (f" + {cov_expr}" if cov_expr else "")
        med_models = {}
        med_pred_cols = {}
        for m in med_list:
            med_formula = f"{m} ~ {exposure}" + (f" + {cov_expr}" if cov_expr else "")
            med_models[m] = fit_linear_model(med_formula, d, weight_col)
            med_pred_cols[m] = [exposure] + covars_used
        return {
            "total_model": fit_linear_model(total_formula, d, weight_col),
            "outcome_model": fit_linear_model(outcome_formula, d, weight_col),
            "mediator_models": med_models,
            "covars_used": covars_used,
            "med_list": med_list,
            "predict_total": _predict_linear,
            "predict_outcome": _predict_linear,
            "predict_mediator": _predict_linear,
            "outcome_feature_cols": [exposure] + med_list + covars_used,
            "total_feature_cols": [exposure] + covars_used,
            "mediator_feature_cols": med_pred_cols,
        }

    med_models = {}
    med_pred_cols = {}
    for i, m in enumerate(med_list):
        feat_cols = [exposure] + covars_used
        med_models[m] = fit_nonlinear_model(d[feat_cols], d[m], seed + 17 * (i + 1), model_type, sample_weight, args)
        med_pred_cols[m] = feat_cols
    outcome_cols = [exposure] + med_list + covars_used
    total_cols = [exposure] + covars_used
    return {
        "total_model": fit_nonlinear_model(d[total_cols], d[outcome], seed + 1001, model_type, sample_weight, args),
        "outcome_model": fit_nonlinear_model(d[outcome_cols], d[outcome], seed + 2001, model_type, sample_weight, args),
        "mediator_models": med_models,
        "covars_used": covars_used,
        "med_list": med_list,
        "predict_total": _predict_nonlinear,
        "predict_outcome": _predict_nonlinear,
        "predict_mediator": _predict_nonlinear,
        "outcome_feature_cols": outcome_cols,
        "total_feature_cols": total_cols,
        "mediator_feature_cols": med_pred_cols,
    }


def compute_effects_once(
    d: pd.DataFrame,
    exposure: str,
    mediators: list[str],
    outcome: str,
    covars: list[str],
    model_type: str,
    seed: int,
    q_low: float,
    q_high: float,
    weight_col: str | None,
    args: argparse.Namespace | None,
) -> tuple[float, float, dict[str, float], float, float]:
    bundle = fit_models(d, exposure, mediators, outcome, covars, model_type, seed, weight_col, args)
    med_list = bundle["med_list"]
    x0, x1 = safe_quantile_pair(d[exposure], q_low, q_high)

    total_base = d[bundle["total_feature_cols"]].copy()
    y_total_x0 = bundle["predict_total"](bundle["total_model"], _set_constant(total_base, exposure, x0))
    y_total_x1 = bundle["predict_total"](bundle["total_model"], _set_constant(total_base, exposure, x1))
    te = float(np.mean(y_total_x1 - y_total_x0))

    med_x0 = {}
    med_x1 = {}
    for m in med_list:
        m_base = d[bundle["mediator_feature_cols"][m]].copy()
        med_x0[m] = bundle["predict_mediator"](bundle["mediator_models"][m], _set_constant(m_base, exposure, x0))
        med_x1[m] = bundle["predict_mediator"](bundle["mediator_models"][m], _set_constant(m_base, exposure, x1))

    out_base = d[bundle["outcome_feature_cols"]].copy()
    out_all_m0 = _set_constant(out_base, exposure, x0)
    out_all_m1 = _set_constant(out_base, exposure, x1)
    for m in med_list:
        out_all_m0 = _set_column(out_all_m0, m, med_x0[m])
        out_all_m1 = _set_column(out_all_m1, m, med_x0[m])

    y_nde_x0 = bundle["predict_outcome"](bundle["outcome_model"], out_all_m0)
    y_nde_x1 = bundle["predict_outcome"](bundle["outcome_model"], out_all_m1)
    nde = float(np.mean(y_nde_x1 - y_nde_x0))

    nie_map = {}
    y_nie_base = bundle["predict_outcome"](bundle["outcome_model"], out_all_m1)
    for m in med_list:
        out_m1 = out_all_m1.copy()
        out_m1 = _set_column(out_m1, m, med_x1[m])
        y_m1 = bundle["predict_outcome"](bundle["outcome_model"], out_m1)
        nie_map[m] = float(np.mean(y_m1 - y_nie_base))

    return te, nde, nie_map, x0, x1


def run_one_combo(
    df: pd.DataFrame,
    exposure: str,
    outcome: str,
    mediators: list[str],
    covars: list[str],
    min_complete_rows: int,
    bootstrap: int,
    seed: int,
    q_low: float,
    q_high: float,
    model_type: str,
    z_covars: list[str],
    g_covars: list[str],
    weight_col: str | None,
    args: argparse.Namespace | None,
) -> pd.DataFrame:
    med_list = [m for m in mediators if m in df.columns]
    req = [exposure, outcome] + med_list + [c for c in covars if c in df.columns]
    if weight_col and weight_col in df.columns:
        req.append(weight_col)
    req = list(dict.fromkeys(req))
    d = df[req].dropna().copy()
    if len(d) < min_complete_rows or not med_list:
        return pd.DataFrame()

    z_used = [c for c in z_covars if c in d.columns]
    g_used = [c for c in g_covars if c in d.columns]

    te_hat, nde_hat, nie_hat, x0, x1 = compute_effects_once(
        d=d,
        exposure=exposure,
        mediators=mediators,
        outcome=outcome,
        covars=covars,
        model_type=model_type,
        seed=seed,
        q_low=q_low,
        q_high=q_high,
        weight_col=weight_col,
        args=args,
    )

    rng = np.random.default_rng(seed)
    te_bs = []
    nde_bs = []
    nie_bs = {m: [] for m in med_list}
    n = len(d)
    for b in range(bootstrap):
        s = d.iloc[rng.integers(0, n, n)].reset_index(drop=True)
        try:
            te_b, nde_b, nie_b, _, _ = compute_effects_once(
                d=s,
                exposure=exposure,
                mediators=mediators,
                outcome=outcome,
                covars=covars,
                model_type=model_type,
                seed=seed + 10000 + b,
                q_low=q_low,
                q_high=q_high,
                weight_col=weight_col,
                args=args,
            )
        except Exception:
            continue
        te_bs.append(te_b)
        nde_bs.append(nde_b)
        for m in med_list:
            nie_bs[m].append(nie_b[m])

    te_bs = np.asarray(te_bs, dtype=float)
    nde_bs = np.asarray(nde_bs, dtype=float)
    te_est = float(np.nanmean(te_bs)) if te_bs.size else float(te_hat)
    nde_est = float(np.nanmean(nde_bs)) if nde_bs.size else float(nde_hat)
    te_lo, te_hi = (np.nan, np.nan) if te_bs.size == 0 else np.nanpercentile(te_bs, [2.5, 97.5])
    nde_lo, nde_hi = (np.nan, np.nan) if nde_bs.size == 0 else np.nanpercentile(nde_bs, [2.5, 97.5])

    rows = []
    for m in med_list:
        arr = np.asarray(nie_bs[m], dtype=float)
        nie_est = float(np.nanmean(arr)) if arr.size else float(nie_hat[m])
        nie_lo, nie_hi = (np.nan, np.nan) if arr.size == 0 else np.nanpercentile(arr, [2.5, 97.5])
        rows.append(
            {
                "Model_Type": model_type,
                "Pathway": f"{exposure} -> {m} -> {outcome} | Z,G",
                "Exposure": exposure,
                "Mediator": m,
                "Outcome": outcome,
                "Z_Covars_Used": "|".join(z_used),
                "G_Covars_Used": "|".join(g_used),
                "Weight_Col_Used": weight_col or "",
                "Contrast_X0": float(x0),
                "Contrast_X1": float(x1),
                "Contrast_Delta": float(x1 - x0),
                "TE_Estimate": te_est,
                "TE_CI_Lower": float(te_lo),
                "TE_CI_Upper": float(te_hi),
                "NDE_Estimate": nde_est,
                "NDE_CI_Lower": float(nde_lo),
                "NDE_CI_Upper": float(nde_hi),
                "NIE_Estimate": float(nie_est),
                "NIE_CI_Lower": float(nie_lo),
                "NIE_CI_Upper": float(nie_hi),
                "NIE_Significant": bool(ci_excludes_zero(float(nie_lo), float(nie_hi))),
                "NIE_SignConsistency": float(np.nanmean(np.sign(arr) == np.sign(nie_est))) if arr.size else float("nan"),
                "N_rows": int(len(d)),
                "Bootstrap_Used": int(te_bs.size),
            }
        )
    return pd.DataFrame(rows)


def run_model(df: pd.DataFrame, args: argparse.Namespace, model_type: str, out_root: Path) -> dict:
    out_dir = out_root / model_type
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        if model_type != "linear":
            make_nonlinear_model(model_type, int(args.seed), args=args)
    except Exception as exc:
        summary = {"model_type": model_type, "status": "unavailable", "error": str(exc)}
        pd.DataFrame([summary]).to_csv(out_dir / "summary.csv", index=False)
        return summary

    all_tables = []
    for ex in args.exposures:
        for out in args.outcomes:
            t = run_one_combo(
                df=df,
                exposure=ex,
                outcome=out,
                mediators=args.mediators,
                covars=args.all_covars,
                min_complete_rows=int(args.min_complete_rows),
                bootstrap=int(args.bootstrap),
                seed=int(args.seed),
                q_low=float(args.contrast_q_low),
                q_high=float(args.contrast_q_high),
                model_type=model_type,
                z_covars=args.z_covars_resolved,
                g_covars=args.g_covars_resolved,
                weight_col=args.weight_col_resolved,
                args=args,
            )
            if t.empty:
                continue
            all_tables.append(t)
            t.to_csv(out_dir / f"mediation_table_{model_type}_{ex}_{out}.csv", index=False)

    if not all_tables:
        summary = {"model_type": model_type, "status": "error", "error": "No valid pathways produced."}
        pd.DataFrame([summary]).to_csv(out_dir / "summary.csv", index=False)
        return summary

    all_df = pd.concat(all_tables, ignore_index=True)
    all_df.to_csv(out_dir / "mediation_table_all_combos.csv", index=False)
    summary = {
        "model_type": model_type,
        "status": "ok",
        "n_pathways": int(len(all_df)),
        "nie_significant_count": int(all_df["NIE_Significant"].sum()),
        "nie_significant_rate": float(all_df["NIE_Significant"].mean()),
        "mean_abs_nie": float(all_df["NIE_Estimate"].abs().mean()),
        "max_abs_nie": float(all_df["NIE_Estimate"].abs().max()),
        "mean_te": float(all_df["TE_Estimate"].mean()),
        "mean_nde": float(all_df["NDE_Estimate"].mean()),
        "n_z_covars": int(len(args.z_covars_resolved)),
        "n_g_covars": int(len(args.g_covars_resolved)),
        "weight_col_used": args.weight_col_resolved or "",
    }
    pd.DataFrame([summary]).to_csv(out_dir / "summary.csv", index=False)

    compact = (
        all_df.groupby(["Model_Type", "Exposure", "Outcome"], as_index=False)
        .agg(
            TE_Estimate=("TE_Estimate", "mean"),
            NDE_Estimate=("NDE_Estimate", "mean"),
            Mean_Abs_NIE=("NIE_Estimate", lambda s: float(s.abs().mean())),
            NIE_Significant_Count=("NIE_Significant", "sum"),
        )
    )
    compact.to_csv(out_dir / "compact_effect_summary.csv", index=False)
    return summary


def main() -> None:
    args = parse_args()
    input_csv = Path(args.input_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    run_cfg = {
        "input_csv": str(input_csv),
        "out_dir": str(out_dir),
        "bootstrap": int(args.bootstrap),
        "seed": int(args.seed),
        "min_complete_rows": int(args.min_complete_rows),
        "contrast_q_low": float(args.contrast_q_low),
        "contrast_q_high": float(args.contrast_q_high),
        "exposures": list(args.exposures),
        "mediators": list(args.mediators),
        "outcomes": list(args.outcomes),
        "covars": list(args.covars),
        "gam_n_knots": int(args.gam_n_knots),
        "gam_degree": int(args.gam_degree),
        "gam_transform": str(args.gam_transform),
        "models": list(args.models),
    }
    (out_dir / "run_config.json").write_text(json.dumps(run_cfg, indent=2), encoding="utf-8")

    df = pd.read_csv(input_csv)
    all_covars, z_covars, g_covars = resolve_covariate_blocks(df, args)
    weight_col = resolve_weight_col(df, args)
    args.all_covars = all_covars
    args.z_covars_resolved = z_covars
    args.g_covars_resolved = g_covars
    args.weight_col_resolved = weight_col

    run_cfg["covars"] = list(all_covars)
    run_cfg["z_covars"] = list(z_covars)
    run_cfg["g_covars"] = list(g_covars)
    run_cfg["weight_col_used"] = weight_col or ""
    (out_dir / "run_config.json").write_text(json.dumps(run_cfg, indent=2), encoding="utf-8")

    requested_models = []
    for model_type in args.models:
        if model_type not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model '{model_type}'. Supported values: {SUPPORTED_MODELS}")
        requested_models.append(model_type)

    summaries = [run_model(df=df, args=args, model_type=model_type, out_root=out_dir) for model_type in requested_models]
    pd.DataFrame(summaries).to_csv(out_dir / "summary_compare.csv", index=False)


if __name__ == "__main__":
    main()
