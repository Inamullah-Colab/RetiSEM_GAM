from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "01_scripts" / "real_data" / "run_realdata_linear_nonlinear_compare.py"
DEMO_DIR = ROOT / "07_reviewer_demo"
GENERATED_DIR = DEMO_DIR / "generated"

PRIMARY_CONFIG = ROOT / "05_results" / "sensitivity_cluster_representative_gcovars_clean" / "run_config.json"
SENSITIVITY_CONFIG = ROOT / "05_results" / "sensitivity_exposure_outcome_cluster_pruned" / "run_config.json"

QUICK_INPUT = ROOT / "00_inputs" / "sample_small" / "sensitivity_cluster_representative_sample50.csv"
QUICK_EXPOSURE = "LBXTR"
QUICK_OUTCOME = "LBXGLU"
QUICK_MEDIATORS = [
    "Artery_Vessel_density",
    "Artery_Fractal_dimension",
    "Artery_Average_width",
    "Artery_Tortuosity_density",
    "Artery_Distance_tortuosity",
    "Vein_Tortuosity_density",
    "Vein_Distance_tortuosity",
]
QUICK_COVARS = [
    "RIDAGEYR",
    "RIAGENDR",
    "RIDRETH1",
    "INDFMPIR",
    "DMDEDUC3",
    "GREF_AMR",
    "GREF_EUR",
    "GREF_SAS",
    "GREF_entropy",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_command_from_config(config: dict, out_dir: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--input-csv",
        str(ROOT / config["input_csv"]),
        "--out-dir",
        str(out_dir),
        "--bootstrap",
        str(config["bootstrap"]),
        "--seed",
        str(config["seed"]),
        "--min-complete-rows",
        str(config["min_complete_rows"]),
        "--contrast-q-low",
        str(config["contrast_q_low"]),
        "--contrast-q-high",
        str(config["contrast_q_high"]),
        "--exposures",
        *config["exposures"],
        "--mediators",
        *config["mediators"],
        "--outcomes",
        *config["outcomes"],
        "--covars",
        *config["covars"],
        "--gam-n-knots",
        str(config["gam_n_knots"]),
        "--gam-degree",
        str(config["gam_degree"]),
        "--gam-transform",
        str(config["gam_transform"]),
        "--models",
        *config["models"],
    ]
    return cmd


def build_quick_command(out_dir: Path) -> list[str]:
    return [
        sys.executable,
        str(RUNNER),
        "--input-csv",
        str(QUICK_INPUT),
        "--out-dir",
        str(out_dir),
        "--bootstrap",
        "3",
        "--seed",
        "2026",
        "--min-complete-rows",
        "30",
        "--contrast-q-low",
        "0.25",
        "--contrast-q-high",
        "0.75",
        "--exposures",
        QUICK_EXPOSURE,
        "--mediators",
        *QUICK_MEDIATORS,
        "--outcomes",
        QUICK_OUTCOME,
        "--covars",
        *QUICK_COVARS,
        "--gam-n-knots",
        "4",
        "--gam-degree",
        "3",
        "--gam-transform",
        "log1p_signed",
        "--models",
        "linear",
        "RetiSEM_GAM",
    ]


def run_command(cmd: list[str]) -> None:
    print("[RUN]", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run reviewer-facing RetiSEM-GAM demos.")
    ap.add_argument(
        "--mode",
        choices=["quick", "primary", "sensitivity"],
        default="quick",
        help="Demo mode: quick smoke test, primary branch reproduction, or sensitivity branch reproduction.",
    )
    ap.add_argument(
        "--results-dir",
        default=None,
        help="Optional output directory. Defaults to 07_reviewer_demo/generated/<mode>.",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.results_dir) if args.results_dir else GENERATED_DIR / args.mode
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "quick":
        cmd = build_quick_command(out_dir)
        run_command(cmd)
        print(f"[DONE] Quick reviewer smoke test written to {out_dir}")
        return

    if args.mode == "primary":
        config = load_json(PRIMARY_CONFIG)
    else:
        config = load_json(SENSITIVITY_CONFIG)

    cmd = build_command_from_config(config, out_dir)
    run_command(cmd)
    print(f"[DONE] {args.mode} reproduction written to {out_dir}")


if __name__ == "__main__":
    main()
