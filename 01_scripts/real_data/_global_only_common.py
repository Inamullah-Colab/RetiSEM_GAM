from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT / "00_inputs"
RAW_INPUT_DIR = INPUT_DIR / "raw_main"
OUTPUT_DIR = ROOT / "03_outputs"
DOCS_DIR = ROOT / "04_docs"
RESULTS_DIR = ROOT / "05_results"
PLOTS_DIR = ROOT / "06_plots"

MERGED_SOURCE = RAW_INPUT_DIR / "nhanes_macular_proxy_merged.csv"
NHANES_SOURCE = RAW_INPUT_DIR / "nhanes_core_for_merge.csv"
MACULAR_SOURCE = RAW_INPUT_DIR / "macular_bc_prepared_with_seq.csv"
PROXY_SOURCE = RAW_INPUT_DIR / "proxy_genetics_for_merge.csv"

EXPOSURES = ["LBXTR", "LBDLDL", "LBXAPB"]
OUTCOMES = [
    "BPXSY2", "BPXDI2", "BPXSY3", "BPXDI3", "BPXSY4", "BPXDI4",
    "LBXGLU", "LBXGH", "LBXIN", "LBXCRP", "LBXSCR", "URXUMA", "URXUCR",
]
Z_COVARS = ["RIDAGEYR", "RIAGENDR", "RIDRETH1", "INDFMPIR", "DMDEDUC3"]
G_COVARS = ["GREF_AMR", "GREF_EUR", "GREF_SAS", "GREF_entropy"]
COVARS = Z_COVARS + G_COVARS
WEIGHT_COLS = ["WTMEC2YR"]
CATEGORICAL = {"RIAGENDR", "RIDRETH1", "DMDEDUC3"}

MAIN_GLOBAL_PANEL = [
    "Fractal_dimension",
    "Vessel_density",
    "Artery_Average_width",
    "Vein_Average_width",
    "Artery_Distance_tortuosity",
    "Vein_Distance_tortuosity",
    "Tortuosity_density",
]

GLOBAL_RETINAL_FEATURES = [
    "Disc_height",
    "Disc_width",
    "Cup_height",
    "Cup_width",
    "CDR_vertical",
    "CDR_horizontal",
    "Fractal_dimension",
    "Vessel_density",
    "Average_width",
    "Distance_tortuosity",
    "Squared_curvature_tortuosity",
    "Tortuosity_density",
    "Artery_Fractal_dimension",
    "Artery_Vessel_density",
    "Artery_Average_width",
    "Artery_Distance_tortuosity",
    "Artery_Squared_curvature_tortuosity",
    "Artery_Tortuosity_density",
    "Vein_Fractal_dimension",
    "Vein_Vessel_density",
    "Vein_Average_width",
    "Vein_Distance_tortuosity",
    "Vein_Squared_curvature_tortuosity",
    "Vein_Tortuosity_density",
]

GLOBAL_PRUNE_CORR_THRESH = 0.90


def safe_write_csv(df: pd.DataFrame, path: Path) -> Path:
    try:
        df.to_csv(path, index=False)
        return path
    except PermissionError:
        fallback = path.with_name(f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}")
        df.to_csv(fallback, index=False)
        return fallback


def safe_write_text(text: str, path: Path) -> Path:
    try:
        path.write_text(text, encoding="utf-8")
        return path
    except PermissionError:
        fallback = path.with_name(f"{path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{path.suffix}")
        fallback.write_text(text, encoding="utf-8")
        return fallback


def protected_keep_order(columns: list[str], protected: list[str]) -> list[str]:
    keep = [c for c in protected if c in columns]
    keep += [c for c in columns if c not in keep]
    return keep


def prune_high_corr(df_num: pd.DataFrame, threshold: float) -> tuple[list[str], list[dict[str, object]]]:
    corr = df_num.corr(method="spearman").abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    keep = list(df_num.columns)
    logs: list[dict[str, object]] = []
    for col in upper.columns:
        if col not in keep:
            continue
        hits = upper.index[upper[col] > threshold].tolist()
        for row in hits:
            if row in keep and col in keep:
                keep.remove(col)
                logs.append(
                    {
                        "dropped_feature": col,
                        "paired_with": row,
                        "abs_corr": float(upper.loc[row, col]),
                        "reason": f"abs_corr>{threshold}",
                    }
                )
                break
    return keep, logs


def compute_vif(df_num: pd.DataFrame) -> pd.Series:
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    x = df_num.values.astype(float)
    return pd.Series([variance_inflation_factor(x, i) for i in range(x.shape[1])], index=df_num.columns)


def signed_log1p_array(x: np.ndarray) -> np.ndarray:
    return np.sign(x) * np.log1p(np.abs(x))


def transform_and_standardize(df: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, dict[str, str]]:
    out = df.copy()
    audit: dict[str, str] = {}
    for c in cols:
        s = pd.to_numeric(out[c], errors="coerce")
        non_na = s.dropna()
        if non_na.empty:
            audit[c] = "all_nan"
            out[c] = s
            continue
        if float(non_na.skew()) > 1.0 or float((non_na > 0).mean()) > 0.95:
            s = pd.Series(signed_log1p_array(s.to_numpy(dtype=float)), index=s.index)
            audit[c] = "signed_log1p+zscore"
        else:
            audit[c] = "zscore"
        sd = float(s.std(skipna=True))
        mu = float(s.mean(skipna=True))
        out[c] = (s - mu) / sd if np.isfinite(sd) and sd > 0 else s - mu
    return out, audit


def make_model_ready(df: pd.DataFrame, mediators: list[str]) -> tuple[pd.DataFrame, dict[str, object], dict[str, str], list[str]]:
    base_keep = [c for c in ["SEQN", "Name"] if c in df.columns]
    exposures = [c for c in EXPOSURES if c in df.columns]
    outcomes = [c for c in OUTCOMES if c in df.columns]
    covars = [c for c in COVARS if c in df.columns]
    z_covars = [c for c in Z_COVARS if c in df.columns]
    g_covars = [c for c in G_COVARS if c in df.columns]
    weights = [c for c in WEIGHT_COLS if c in df.columns]
    mediators = [c for c in mediators if c in df.columns]

    keep_cols = base_keep + exposures + outcomes + mediators
    keep_cols += [c for c in covars if c not in keep_cols]
    keep_cols += [c for c in weights if c not in keep_cols]
    out = df[keep_cols].copy()

    numeric_cols = [c for c in out.columns if c not in {"SEQN", "Name"} | CATEGORICAL]
    transform_cols = [c for c in numeric_cols if c not in set(weights)]
    for c in numeric_cols:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out[numeric_cols] = out[numeric_cols].replace({7: np.nan, 9: np.nan, 77: np.nan, 99: np.nan, 777: np.nan, 999: np.nan})

    out_scaled, transform_audit = transform_and_standardize(out, transform_cols)
    for c in weights:
        if c in out_scaled.columns:
            transform_audit[c] = "raw_weight"
    out_imputed = out_scaled.copy()
    for c in numeric_cols:
        med = pd.to_numeric(out_imputed[c], errors="coerce").median(skipna=True)
        out_imputed[c] = pd.to_numeric(out_imputed[c], errors="coerce").fillna(med)
    for c in [x for x in covars if x in CATEGORICAL]:
        mode = out_imputed[c].mode(dropna=True)
        if not mode.empty:
            out_imputed[c] = out_imputed[c].fillna(mode.iloc[0])

    all_nan_after = [c for c in out_imputed.columns if out_imputed[c].isna().all()]
    if all_nan_after:
        out_imputed = out_imputed.drop(columns=all_nan_after, errors="ignore")
        mediators = [c for c in mediators if c not in all_nan_after]
        outcomes = [c for c in outcomes if c not in all_nan_after]

    role_map = {
        "exposures": exposures,
        "outcomes": outcomes,
        "mediators": mediators,
        "covars": covars,
        "z_covars": z_covars,
        "g_covars": g_covars,
        "weights": weights,
        "categorical_covars": [c for c in covars if c in CATEGORICAL],
    }
    return out_imputed, role_map, transform_audit, all_nan_after
