from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "01_scripts" / "real_data" / "run_realdata_linear_nonlinear_compare.py"

BRANCH = "sensitivity_exposure_outcome_cluster_pruned"


def main() -> None:
    input_csv = Path("03_outputs") / f"{BRANCH}.csv"
    roles = json.loads((ROOT / "03_outputs" / f"{BRANCH}_roles.json").read_text(encoding="utf-8"))
    out_dir = Path("05_results") / BRANCH
    cmd = [
        sys.executable,
        str(RUNNER),
        "--input-csv",
        str(input_csv),
        "--out-dir",
        str(out_dir),
        "--bootstrap",
        "10",
        "--seed",
        "2026",
        "--min-complete-rows",
        "250",
        "--contrast-q-low",
        "0.25",
        "--contrast-q-high",
        "0.75",
        "--gam-n-knots",
        "4",
        "--gam-degree",
        "3",
        "--gam-transform",
        "log1p_signed",
        "--models",
        "linear",
        "RetiSEM_GAM",
        "--weight-col",
        roles["weights"][0],
        "--exposures",
        *roles["exposures"],
        "--mediators",
        *roles["mediators"],
        "--outcomes",
        *roles["outcomes"],
        "--covars",
        *roles["covars"],
        "--z-covars",
        *roles["z_covars"],
        "--g-covars",
        *roles["g_covars"],
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    print(out_dir)


if __name__ == "__main__":
    main()
