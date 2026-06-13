from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from _global_only_common import GLOBAL_RETINAL_FEATURES, OUTPUT_DIR, PLOTS_DIR


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "04_docs"

EXPOSURE_OUTCOME_COLS = [
    "LBXTR",
    "LBDLDL",
    "LBXAPB",
    "BPXSY2",
    "BPXDI2",
    "BPXSY3",
    "BPXDI3",
    "BPXSY4",
    "BPXDI4",
    "LBXGLU",
    "LBXGH",
    "LBXIN",
    "LBXCRP",
    "LBXSCR",
    "URXUMA",
    "URXUCR",
]


def plot_cluster_heatmap(corr: pd.DataFrame, title: str, out_path: Path) -> None:
    dist = 1.0 - corr.abs()
    np.fill_diagonal(dist.values, 0.0)
    linkage_matrix = linkage(squareform(dist.to_numpy(), checks=False), method="average")
    order = dendrogram(linkage_matrix, no_plot=True)["leaves"]
    ordered = corr.iloc[order, order]

    fig = plt.figure(figsize=(13, 11))
    gs = fig.add_gridspec(2, 2, width_ratios=[0.18, 1], height_ratios=[0.22, 1], wspace=0.02, hspace=0.02)
    ax_top = fig.add_subplot(gs[0, 1])
    ax_left = fig.add_subplot(gs[1, 0])
    ax_heat = fig.add_subplot(gs[1, 1])

    dendrogram(linkage_matrix, ax=ax_top, color_threshold=0, above_threshold_color="#666666", no_labels=True)
    ax_top.axis("off")
    dendrogram(linkage_matrix, ax=ax_left, orientation="left", color_threshold=0, above_threshold_color="#666666", no_labels=True)
    ax_left.axis("off")

    arr = ordered.to_numpy(dtype=float)
    im = ax_heat.imshow(arr, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
    ax_heat.set_xticks(np.arange(len(ordered.columns)))
    ax_heat.set_xticklabels(ordered.columns, rotation=60, ha="right", fontsize=9)
    ax_heat.set_yticks(np.arange(len(ordered.index)))
    ax_heat.set_yticklabels(ordered.index, fontsize=9)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax_heat.text(j, i, f"{arr[i, j]:.2f}", ha="center", va="center", fontsize=7, color="black")
    cbar = fig.colorbar(im, ax=ax_heat, fraction=0.046, pad=0.04)
    cbar.set_label("Pearson correlation")
    fig.suptitle(title, fontsize=18, fontweight="bold", y=0.98)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(OUTPUT_DIR / "merged_full_global_only_source.csv")
    eo_cols = [c for c in EXPOSURE_OUTCOME_COLS if c in df.columns]
    rt_cols = [c for c in GLOBAL_RETINAL_FEATURES if c in df.columns]

    eo = df[eo_cols].apply(pd.to_numeric, errors="coerce").fillna(df[eo_cols].median(numeric_only=True))
    rt = df[rt_cols].apply(pd.to_numeric, errors="coerce").fillna(df[rt_cols].median(numeric_only=True))

    eo_corr = eo.corr(method="pearson")
    rt_corr = rt.corr(method="pearson")

    eo_corr.to_csv(DOCS_DIR / "exposure_outcome_pearson_corr.csv")
    rt_corr.to_csv(DOCS_DIR / "global_retinal_pearson_corr.csv")

    plot_cluster_heatmap(
        eo_corr,
        "Exposure and Outcome Pearson Correlation with Hierarchical Clustering",
        PLOTS_DIR / "exposure_outcome_cluster_heatmap.png",
    )
    plot_cluster_heatmap(
        rt_corr,
        "Global Retinal Feature Pearson Correlation with Hierarchical Clustering",
        PLOTS_DIR / "global_retinal_cluster_heatmap.png",
    )
    print(PLOTS_DIR / "exposure_outcome_cluster_heatmap.png")
    print(PLOTS_DIR / "global_retinal_cluster_heatmap.png")


if __name__ == "__main__":
    main()
