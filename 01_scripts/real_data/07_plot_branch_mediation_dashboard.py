from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / "05_results"
PLOTS_ROOT = ROOT / "06_plots"
PLOTS_ROOT.mkdir(exist_ok=True)

METHOD_ORDER = ["linear", "RetiSEM_GAM"]
METHOD_LABELS = {"linear": "Linear", "RetiSEM_GAM": "RetiSEM_GAM"}
METHOD_COLORS = {"linear": "#4361EE", "RetiSEM_GAM": "#2E7D32"}

BRANCH_SPECS = [
    {
        "name": "sensitivity_cluster_representative_gcovars_clean",
        "title": "Global-Only Retinal Linear vs RetiSEM_GAM Mediation Comparison",
        "subtitle": "Cluster-derived representative retinal biomarkers. Lipids are exposures; proxy genetics are covariates.",
        "outfile": "cluster_representative_mediation_dashboard.png",
    },
    {
        "name": "sensitivity_exposure_outcome_cluster_pruned",
        "title": "Exposure/Outcome + Cluster-Retinal Pruned Linear vs RetiSEM_GAM Comparison",
        "subtitle": "Pruned lipid exposures, pruned clinical outcomes, and cluster-representative retinal mediators with Z and G adjustment.",
        "outfile": "exposure_outcome_cluster_pruned_mediation_dashboard.png",
    },
]


def load_branch_tables(branch_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    branch_dir = RESULTS_ROOT / branch_name
    linear = pd.read_csv(branch_dir / "linear" / "mediation_table_all_combos.csv")
    gam = pd.read_csv(branch_dir / "RetiSEM_GAM" / "mediation_table_all_combos.csv")
    return linear, gam


def load_branch_summary(branch_name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS_ROOT / branch_name / "summary_compare.csv")


def effect_summary(df: pd.DataFrame) -> pd.DataFrame:
    out = (
        df.groupby(["Exposure", "Outcome"], as_index=False)
        .agg(
            mean_abs_nie=("NIE_Estimate", lambda s: np.mean(np.abs(s))),
            mean_te=("TE_Estimate", "mean"),
            mean_nde=("NDE_Estimate", "mean"),
        )
        .copy()
    )
    out["pair"] = out["Exposure"] + " -> " + out["Outcome"]
    return out


def te_pairs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.groupby(["Exposure", "Outcome"], as_index=False)["TE_Estimate"].mean().copy()
    out["pair"] = out["Exposure"] + " -> " + out["Outcome"]
    return out


def draw_dashboard(branch_name: str, title: str, subtitle: str, outfile: str) -> Path:
    linear_df, gam_df = load_branch_tables(branch_name)
    summary_df = load_branch_summary(branch_name).set_index("model_type")

    linear_fx = effect_summary(linear_df)
    gam_fx = effect_summary(gam_df)
    merged_fx = linear_fx.merge(
        gam_fx,
        on=["Exposure", "Outcome", "pair"],
        suffixes=("_linear", "_gam"),
    )
    merged_fx = merged_fx.sort_values("mean_abs_nie_linear", ascending=False).reset_index(drop=True)

    linear_te = te_pairs(linear_df)
    gam_te = te_pairs(gam_df)
    merged_te = linear_te.merge(gam_te, on=["Exposure", "Outcome", "pair"], suffixes=("_linear", "_gam"))
    merged_te = merged_te.sort_values("TE_Estimate_linear", ascending=False).reset_index(drop=True)
    te_display = merged_te.head(14).copy()
    bar_display = merged_fx.head(20).copy()

    fig = plt.figure(figsize=(17, 11), facecolor="white")
    gs = fig.add_gridspec(2, 3, height_ratios=[0.95, 1.25], width_ratios=[0.9, 1.15, 1.55], hspace=0.28, wspace=0.22)

    ax_count = fig.add_subplot(gs[0, 0])
    ax_summary = fig.add_subplot(gs[0, 1])
    ax_te = fig.add_subplot(gs[0, 2])
    ax_bar = fig.add_subplot(gs[1, :])

    # Significant NIE count
    counts = [summary_df.loc[m, "nie_significant_count"] for m in METHOD_ORDER]
    x = np.arange(len(METHOD_ORDER))
    bars = ax_count.bar(x, counts, color=[METHOD_COLORS[m] for m in METHOD_ORDER], width=0.55)
    for bar, value in zip(bars, counts):
        ax_count.text(bar.get_x() + bar.get_width() / 2, value + max(counts) * 0.02 + 0.2, f"{int(value)}", ha="center", va="bottom", fontsize=14, fontweight="bold")
    ax_count.set_xticks(x)
    ax_count.set_xticklabels([METHOD_LABELS[m] for m in METHOD_ORDER], fontsize=13)
    ax_count.set_title("Significant NIE Pathways", loc="left", fontsize=17, fontweight="bold")
    ax_count.grid(axis="y", alpha=0.22)
    ax_count.spines["top"].set_visible(False)
    ax_count.spines["right"].set_visible(False)

    # Summary metrics
    ax_summary.set_title("Summary Metrics", loc="left", fontsize=17, fontweight="bold")
    ax_summary.set_xlim(0, 1)
    ax_summary.set_ylim(0, 1)
    ax_summary.axis("off")
    metrics = [
        ("Mean |NIE|", "mean_abs_nie"),
        ("Max |NIE|", "max_abs_nie"),
        ("Mean TE", "mean_te"),
        ("Mean NDE", "mean_nde"),
    ]
    y_positions = [0.85, 0.62, 0.39, 0.16]
    for (label, key), ypos in zip(metrics, y_positions):
        ax_summary.text(0.00, ypos, label, fontsize=14, va="center")
        ax_summary.text(0.68, ypos, f"{summary_df.loc['linear', key]:.5f}", color=METHOD_COLORS["linear"], fontsize=14, va="center", ha="right", fontweight="bold")
        ax_summary.text(0.98, ypos, f"{summary_df.loc['RetiSEM_GAM', key]:.5f}", color=METHOD_COLORS["RetiSEM_GAM"], fontsize=14, va="center", ha="right", fontweight="bold")
        if ypos > 0.12:
            ax_summary.hlines(ypos - 0.09, 0.0, 1.0, color="#E0E0E0", linewidth=1)
    ax_summary.text(0.68, 0.03, "Linear", color=METHOD_COLORS["linear"], fontsize=12, ha="right")
    ax_summary.text(0.98, 0.03, "RetiSEM_GAM", color=METHOD_COLORS["RetiSEM_GAM"], fontsize=12, ha="right")

    # TE comparison
    y = np.arange(len(te_display))
    ax_te.axvline(0.0, color="#D9DEE6", linewidth=1)
    ax_te.hlines(y, te_display["TE_Estimate_linear"], te_display["TE_Estimate_gam"], color="#9AA5B1", linewidth=1.4, alpha=0.9)
    ax_te.scatter(te_display["TE_Estimate_linear"], y, color=METHOD_COLORS["linear"], s=28, label="Linear", zorder=3)
    ax_te.scatter(te_display["TE_Estimate_gam"], y, color=METHOD_COLORS["RetiSEM_GAM"], s=28, label="RetiSEM_GAM", zorder=3)
    ax_te.set_yticks(y)
    ax_te.set_yticklabels(te_display["pair"], fontsize=10)
    ax_te.invert_yaxis()
    ax_te.set_title("Exposure-Outcome TE Comparison", loc="left", fontsize=17, fontweight="bold")
    ax_te.grid(axis="x", alpha=0.18)
    ax_te.legend(frameon=False, loc="lower right")
    ax_te.spines["top"].set_visible(False)
    ax_te.spines["right"].set_visible(False)

    # Mean absolute NIE by pair
    pairs = bar_display["pair"].tolist()
    bx = np.arange(len(pairs))
    width = 0.38
    ax_bar.bar(bx - width / 2, bar_display["mean_abs_nie_linear"], width=width, color=METHOD_COLORS["linear"], label="Linear")
    ax_bar.bar(bx + width / 2, bar_display["mean_abs_nie_gam"], width=width, color=METHOD_COLORS["RetiSEM_GAM"], label="RetiSEM_GAM")
    ax_bar.set_xticks(bx)
    ax_bar.set_xticklabels(pairs, rotation=45, ha="right", fontsize=10)
    ax_bar.set_title("Mean |NIE| by Exposure-Outcome", loc="left", fontsize=17, fontweight="bold")
    ax_bar.text(
        0.0,
        1.02,
        "Ordered by linear mean |NIE|. Larger bars indicate stronger average mediated effect across retained retinal pathways.",
        transform=ax_bar.transAxes,
        fontsize=11,
        color="#5B6777",
    )
    ax_bar.grid(axis="y", alpha=0.22)
    ax_bar.legend(frameon=False, ncol=2, loc="upper left")
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)

    fig.suptitle(title, x=0.04, y=0.975, ha="left", fontsize=20, fontweight="bold")
    fig.text(0.04, 0.945, subtitle, ha="left", fontsize=11.5, color="#5B6777")

    out_path = PLOTS_ROOT / outfile
    fig.savefig(out_path, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    outputs = []
    for spec in BRANCH_SPECS:
        outputs.append(
            draw_dashboard(
                branch_name=spec["name"],
                title=spec["title"],
                subtitle=spec["subtitle"],
                outfile=spec["outfile"],
            )
        )
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
