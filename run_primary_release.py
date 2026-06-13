from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_step(script_rel: str) -> None:
    script = ROOT / script_rel
    print(f"[RUN] {script_rel}")
    subprocess.run([sys.executable, str(script)], check=True, cwd=ROOT)


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the main GitHub release workflow.")
    ap.add_argument(
        "--with-sensitivity",
        action="store_true",
        help="Also run the stricter exposure/outcome-pruned sensitivity branch.",
    )
    args = ap.parse_args()

    primary_steps = [
        "01_scripts/real_data/01_build_global_only_branches.py",
        "01_scripts/real_data/02_run_global_only_comparisons.py",
        "01_scripts/real_data/03_plot_global_only_comparison.py",
        "01_scripts/real_data/05_plot_cluster_heatmaps.py",
        "01_scripts/real_data/07_plot_branch_mediation_dashboard.py",
        "01_scripts/real_data/08_plot_top_pathways_forest.py",
    ]

    sensitivity_steps = [
        "01_scripts/real_data/04_build_exposure_outcome_cluster_pruned_branch.py",
        "01_scripts/real_data/06_run_exposure_outcome_cluster_pruned_comparison.py",
        "01_scripts/real_data/05_plot_cluster_heatmaps.py",
        "01_scripts/real_data/07_plot_branch_mediation_dashboard.py",
        "01_scripts/real_data/08_plot_top_pathways_forest.py",
    ]

    for step in primary_steps:
        run_step(step)

    if args.with_sensitivity:
        for step in sensitivity_steps:
            run_step(step)

    print("[DONE] GitHub release workflow finished.")


if __name__ == "__main__":
    main()
