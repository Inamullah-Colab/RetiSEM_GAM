from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / "05_results"
PLOTS_ROOT = ROOT / "06_plots"
PLOTS_ROOT.mkdir(exist_ok=True)

SIG_COLOR = "#C62828"
SIG_HIGHLIGHT = "#F9A825"

PLOT_SPECS = [
    {
        "branch": "sensitivity_cluster_representative_gcovars_clean",
        "model": "linear",
        "title": "Top 30 Pathways by |NIE| (Linear, Cluster-Derived Global Retinal Branch)",
        "outfile": "forest_top30_linear_cluster_representative.png",
        "top_n": 30,
    },
    {
        "branch": "sensitivity_cluster_representative_gcovars_clean",
        "model": "RetiSEM_GAM",
        "title": "Top 30 Pathways by |NIE| (RetiSEM_GAM, Cluster-Derived Global Retinal Branch)",
        "outfile": "forest_top30_gam_cluster_representative.png",
        "top_n": 30,
    },
    {
        "branch": "sensitivity_exposure_outcome_cluster_pruned",
        "model": "linear",
        "title": "Top 30 Pathways by |NIE| (Linear, Exposure/Outcome + Cluster-Retinal Pruned Branch)",
        "outfile": "forest_top30_linear_exposure_outcome_cluster_pruned.png",
        "top_n": 30,
    },
    {
        "branch": "sensitivity_exposure_outcome_cluster_pruned",
        "model": "RetiSEM_GAM",
        "title": "Top 30 Pathways by |NIE| (RetiSEM_GAM, Exposure/Outcome + Cluster-Retinal Pruned Branch)",
        "outfile": "forest_top30_gam_exposure_outcome_cluster_pruned.png",
        "top_n": 30,
    },
    {
        "branch": "sensitivity_cluster_representative_gcovars_clean",
        "model": "linear",
        "title": "All Pathways by |NIE| (Linear, Cluster-Derived Global Retinal Branch)",
        "outfile": "forest_all_linear_cluster_representative.png",
        "top_n": None,
    },
    {
        "branch": "sensitivity_cluster_representative_gcovars_clean",
        "model": "RetiSEM_GAM",
        "title": "All Pathways by |NIE| (RetiSEM_GAM, Cluster-Derived Global Retinal Branch)",
        "outfile": "forest_all_gam_cluster_representative.png",
        "top_n": None,
    },
    {
        "branch": "sensitivity_exposure_outcome_cluster_pruned",
        "model": "linear",
        "title": "All Pathways by |NIE| (Linear, Exposure/Outcome + Cluster-Retinal Pruned Branch)",
        "outfile": "forest_all_linear_exposure_outcome_cluster_pruned.png",
        "top_n": None,
    },
    {
        "branch": "sensitivity_exposure_outcome_cluster_pruned",
        "model": "RetiSEM_GAM",
        "title": "All Pathways by |NIE| (RetiSEM_GAM, Exposure/Outcome + Cluster-Retinal Pruned Branch)",
        "outfile": "forest_all_gam_exposure_outcome_cluster_pruned.png",
        "top_n": None,
    },
]


def format_pathway_label(pathway: str, significant: bool) -> str:
    label = pathway
    if significant:
        label = f"{label} *"
    return label


def draw_forest(branch: str, model: str, title: str, outfile: str, top_n: int | None = 30) -> Path:
    csv_path = RESULTS_ROOT / branch / model / "mediation_table_all_combos.csv"
    df = pd.read_csv(csv_path)
    df["abs_nie"] = df["NIE_Estimate"].abs()
    ordered = df.sort_values("abs_nie", ascending=False)
    top = ordered.head(top_n).copy() if top_n is not None else ordered.copy()
    top = top.iloc[::-1].reset_index(drop=True)
    top["Pathway_Label"] = [
        format_pathway_label(pathway, significant)
        for pathway, significant in zip(top["Pathway"], top["NIE_Significant"])
    ]

    y = np.arange(len(top))
    fig_height = max(10, 0.42 * len(top) + 1.5)
    fig, ax = plt.subplots(figsize=(14, fig_height))
    ax.axvline(0.0, color="#9E9E9E", linestyle="--", linewidth=1)

    def plot_effect(estimate_col: str, lower_col: str, upper_col: str, color: str, marker: str, label: str, y_offset: float) -> None:
        y_pos = y + y_offset
        x = top[estimate_col].to_numpy()
        xerr = np.vstack([
            x - top[lower_col].to_numpy(),
            top[upper_col].to_numpy() - x,
        ])
        ax.errorbar(
            x,
            y_pos,
            xerr=xerr,
            fmt=marker,
            color=color,
            ecolor=color,
            elinewidth=1.2,
            capsize=2.5,
            markersize=5,
            label=label,
            alpha=0.95,
        )

    plot_effect("TE_Estimate", "TE_CI_Lower", "TE_CI_Upper", "#3B82F6", "o", "TE", -0.20)
    plot_effect("NDE_Estimate", "NDE_CI_Lower", "NDE_CI_Upper", "#43A047", "s", "NDE", 0.00)
    plot_effect("NIE_Estimate", "NIE_CI_Lower", "NIE_CI_Upper", SIG_COLOR, "^", "NIE", 0.20)

    # Add asterisk marker directly on significant NIE estimates for quick visual identification.
    sig = top[top["NIE_Significant"].fillna(False)].copy()
    if not sig.empty:
        sig_y = sig.index.to_numpy() + 0.20
        ax.scatter(
            sig["NIE_Estimate"],
            sig_y,
            marker="*",
            s=95,
            color=SIG_HIGHLIGHT,
            edgecolor="white",
            linewidth=0.6,
            zorder=5,
            label="NIE significant",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(top["Pathway_Label"], fontsize=10)
    for tick, significant in zip(ax.get_yticklabels(), top["NIE_Significant"].tolist()):
        if bool(significant):
            tick.set_color(SIG_HIGHLIGHT)
            tick.set_fontweight("bold")
    ax.set_xlabel("Effect Size", fontsize=13)
    ax.set_title(title, fontsize=18, pad=10)
    ax.grid(axis="x", alpha=0.18)
    ax.text(
        0.995,
        0.015,
        "* marks NIE-significant pathways",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=10,
        color=SIG_HIGHLIGHT,
    )
    ax.legend(loc="lower left", frameon=True)

    out_path = PLOTS_ROOT / outfile
    fig.tight_layout()
    fig.savefig(out_path, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    outputs = []
    for spec in PLOT_SPECS:
        outputs.append(draw_forest(**spec))
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
