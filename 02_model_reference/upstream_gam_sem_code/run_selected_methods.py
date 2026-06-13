#!/usr/bin/env python3
"""Convenience launcher for the GAM-SEM stage benchmark runner."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_METHODS = ["PC", "LINGAM", "DAGMA", "NOTEARS", "DECI", "RetiSEM"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run selected methods for the GAM-SEM stage.")
    ap.add_argument("--scenario", default="LowDim-N")
    ap.add_argument("--impute", default="knn", choices=["auto", "none", "mean", "median", "most_frequent", "knn", "iterative"])
    ap.add_argument("--threshold-q", type=float, default=0.35)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument(
        "--our-sem-variant",
        default="domain_structured_gam",
        choices=["base", "truth_aligned", "domain_structured", "domain_latent", "domain_structured_gam", "gam_sem"],
    )
    ap.add_argument("--our-sem-transform", default="none", choices=["none", "log1p_signed"])
    ap.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    ap.add_argument("--root", default=None, help="Root containing dataset/data and dataset/truth")
    ap.add_argument("--data-root", default=None, help="Explicit data root")
    ap.add_argument("--truth-root", default=None, help="Explicit truth root")
    ap.add_argument("--out", default="results_selected_methods")
    args = ap.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    release_root = scripts_dir.parent
    runner = scripts_dir / "run_gam_benchmark_sem_model.py"

    dataset_root = Path(args.root) if args.root else (release_root / "dataset")
    data_root = Path(args.data_root) if args.data_root else (dataset_root / "data")
    truth_root = Path(args.truth_root) if args.truth_root else (dataset_root / "truth")
    out_dir = release_root / args.out

    cmd = [
        sys.executable,
        str(runner),
        "--root",
        str(release_root),
        "--data_root",
        str(data_root),
        "--truth_root",
        str(truth_root),
        "--scenario",
        str(args.scenario),
        "--methods",
        *[str(m) for m in args.methods],
        "--impute",
        str(args.impute),
        "--threshold_q",
        str(args.threshold_q),
        "--alpha",
        str(args.alpha),
        "--our_sem_variant",
        str(args.our_sem_variant),
        "--our_sem_transform",
        str(args.our_sem_transform),
        "--use_domain_priors",
        "--out",
        str(out_dir),
    ]

    print("Running command:")
    print(" ".join(cmd))
    p = subprocess.run(cmd, env=os.environ.copy())
    if p.returncode != 0:
        return p.returncode

    print("\nSaved outputs:")
    print(f"- {out_dir / args.scenario / 'metrics.csv'}")
    print(f"- {out_dir / args.scenario / 'run_diagnostics.json'}")
    print(f"- {out_dir / 'combined_metrics.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
