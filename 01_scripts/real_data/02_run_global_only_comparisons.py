from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "01_scripts" / "real_data" / "run_realdata_linear_nonlinear_compare.py"
OUTPUT_DIR = ROOT / "03_outputs"
RESULTS_DIR = ROOT / "05_results"
RESULTS_DIR.mkdir(exist_ok=True)

BRANCHES = ["sensitivity_cluster_representative"]


def run_branch(branch: str) -> None:
    input_csv = Path("03_outputs") / f"{branch}.csv"
    roles = json.loads((OUTPUT_DIR / f"{branch}_roles.json").read_text(encoding="utf-8"))
    out_dir = Path("05_results") / "sensitivity_cluster_representative_gcovars_clean"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--input-csv", str(input_csv),
        "--out-dir", str(out_dir),
        "--bootstrap", "10",
        "--seed", "2026",
        "--min-complete-rows", "250",
        "--contrast-q-low", "0.25",
        "--contrast-q-high", "0.75",
        "--gam-n-knots", "4",
        "--gam-degree", "3",
        "--gam-transform", "log1p_signed",
        "--models", "linear", "RetiSEM_GAM",
        "--weight-col", roles["weights"][0],
        "--exposures", *roles["exposures"],
        "--mediators", *roles["mediators"],
        "--outcomes", *roles["outcomes"],
        "--covars", *roles["covars"],
        "--z-covars", *roles.get("z_covars", roles["covars"]),
        "--g-covars", *(roles.get("g_covars", []) or ["NONE"]),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)


def combine_summary() -> None:
    frames = []
    for branch in BRANCHES:
        df = pd.read_csv(RESULTS_DIR / "sensitivity_cluster_representative_gcovars_clean" / "summary_compare.csv")
        df.insert(0, "analysis_branch", branch)
        frames.append(df)
    pd.concat(frames, ignore_index=True).to_csv(RESULTS_DIR / "global_only_summary_compare.csv", index=False)


def main() -> None:
    for branch in BRANCHES:
        print(f"Running {branch}")
        run_branch(branch)
    combine_summary()
    print("Finished global-only comparisons.")


if __name__ == "__main__":
    main()
