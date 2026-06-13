from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "05_results"
RESULTS = RESULTS_DIR / "global_only_summary_compare.csv"
OUT = ROOT / "06_plots"
OUT.mkdir(exist_ok=True)

BRANCH_ORDER = ["sensitivity_cluster_representative"]
BRANCH_LABELS = {
    "sensitivity_cluster_representative": "Cluster Representative",
}
METHOD_ORDER = ["linear", "RetiSEM_GAM"]
METHOD_COLORS = {"linear": "#3D5AFE", "RetiSEM_GAM": "#2E7D32"}
METHOD_LABELS = {"linear": "Linear", "RetiSEM_GAM": "RetiSEM_GAM"}


def main() -> None:
    if not RESULTS.exists():
        frames = []
        for branch in BRANCH_ORDER:
            branch_dir = RESULTS_DIR / (
                "sensitivity_cluster_representative_gcovars_clean"
                if branch == "sensitivity_cluster_representative"
                else branch
            )
            if branch_dir.exists():
                df_branch = pd.read_csv(branch_dir / "summary_compare.csv")
                df_branch.insert(0, "analysis_branch", branch)
                frames.append(df_branch)
        if not frames:
            raise FileNotFoundError(f"No summary sources found under {RESULTS_DIR}")
        pd.concat(frames, ignore_index=True).to_csv(RESULTS, index=False)

    df = pd.read_csv(RESULTS)
    df = df[df["analysis_branch"].isin(BRANCH_ORDER)].copy()

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    axes = axes.flatten()
    metrics = [
        ("nie_significant_count", "Significant NIE Pathways"),
        ("nie_significant_rate", "Significant NIE Rate"),
        ("mean_abs_nie", "Mean |NIE|"),
        ("max_abs_nie", "Max |NIE|"),
    ]
    x = range(len(BRANCH_ORDER))
    width = 0.34

    for ax, (metric, title) in zip(axes, metrics):
        for i, model in enumerate(METHOD_ORDER):
            sub = df[df["model_type"] == model].set_index("analysis_branch").reindex(BRANCH_ORDER)
            xpos = [k + (i - 0.5) * width for k in x]
            ax.bar(xpos, sub[metric], width=width, color=METHOD_COLORS[model], label=METHOD_LABELS[model], alpha=0.95)
        ax.set_title(title, loc="left", fontsize=15, fontweight="bold")
        ax.set_xticks(list(x))
        ax.set_xticklabels([BRANCH_LABELS[b] for b in BRANCH_ORDER], rotation=12, ha="right")
        ax.grid(axis="y", alpha=0.25)
        if metric == "nie_significant_rate":
            ax.yaxis.set_major_formatter(lambda v, pos: f"{v:.1%}")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.98))
    fig.suptitle("Global-Only Retinal Biomarker Analysis", fontsize=22, fontweight="bold", y=0.995)
    fig.text(0.5, 0.955, "Cluster-representative global retinal branch, with zone B and zone C fully excluded.", ha="center", fontsize=11, color="#4C5A6A")
    out = OUT / "global_only_comparison_dashboard.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
