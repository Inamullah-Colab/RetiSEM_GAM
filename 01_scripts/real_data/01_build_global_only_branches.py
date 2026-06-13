from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from _global_only_common import (
    DOCS_DIR,
    GLOBAL_PRUNE_CORR_THRESH,
    GLOBAL_RETINAL_FEATURES,
    MAIN_GLOBAL_PANEL,
    MACULAR_SOURCE,
    NHANES_SOURCE,
    OUTPUT_DIR,
    PROXY_SOURCE,
    make_model_ready,
    protected_keep_order,
    prune_high_corr,
    safe_write_csv,
    safe_write_text,
)

PAPER_CLUSTER_FEATURES = [
    "Artery_Vessel_density",
    "Artery_Fractal_dimension",
    "Vein_Fractal_dimension",
    "Vein_Vessel_density",
    "Artery_Average_width",
    "Vein_Average_width",
    "Artery_Tortuosity_density",
    "Artery_Distance_tortuosity",
    "Artery_Squared_curvature_tortuosity",
    "Vein_Tortuosity_density",
    "Vein_Distance_tortuosity",
    "Vein_Squared_curvature_tortuosity",
]

PAPER_CLUSTER_REPRESENTATIVE_PRIORITY = [
    "Artery_Vessel_density",
    "Artery_Fractal_dimension",
    "Artery_Average_width",
    "Vein_Average_width",
    "Artery_Tortuosity_density",
    "Artery_Distance_tortuosity",
    "Vein_Tortuosity_density",
    "Vein_Distance_tortuosity",
]

PAPER_CLUSTER_THRESHOLD = 0.7


def build_global_pruned_mediators(df: pd.DataFrame) -> tuple[list[str], list[dict[str, object]]]:
    global_cols = [c for c in GLOBAL_RETINAL_FEATURES if c in df.columns]
    retinal_df = df[global_cols].apply(pd.to_numeric, errors="coerce")
    retinal_df = retinal_df.fillna(retinal_df.median(numeric_only=True))
    retinal_df = retinal_df[protected_keep_order(list(retinal_df.columns), MAIN_GLOBAL_PANEL)]

    corr_keep, corr_log_all = prune_high_corr(retinal_df, GLOBAL_PRUNE_CORR_THRESH)
    corr_log: list[dict[str, object]] = []
    for row in corr_log_all:
        dropped = str(row["dropped_feature"])
        paired = str(row["paired_with"])
        if dropped in MAIN_GLOBAL_PANEL and paired not in MAIN_GLOBAL_PANEL:
            corr_keep.append(dropped)
            if paired in corr_keep:
                corr_keep.remove(paired)
            corr_log.append(
                {
                    "dropped_feature": paired,
                    "paired_with": dropped,
                    "abs_corr": row["abs_corr"],
                    "reason": f"abs_corr>{GLOBAL_PRUNE_CORR_THRESH}|protected_swap",
                }
            )
        elif dropped not in MAIN_GLOBAL_PANEL:
            corr_log.append(row)
    corr_keep = protected_keep_order(list(dict.fromkeys(corr_keep)), MAIN_GLOBAL_PANEL)
    return corr_keep, corr_log


def build_paper_cluster_branch(df: pd.DataFrame) -> tuple[list[str], pd.DataFrame, pd.DataFrame]:
    cols = [c for c in PAPER_CLUSTER_FEATURES if c in df.columns]
    sub = df[cols].apply(pd.to_numeric, errors="coerce")
    sub = sub.fillna(sub.median(numeric_only=True))
    pearson = sub.corr(method="pearson")
    dist = 1.0 - pearson.abs()
    np.fill_diagonal(dist.values, 0.0)
    linkage_matrix = linkage(squareform(dist.to_numpy(), checks=False), method="average")
    cluster_ids = fcluster(linkage_matrix, t=1.0 - PAPER_CLUSTER_THRESHOLD, criterion="distance")

    cluster_df = pd.DataFrame(
        {
            "feature": cols,
            "cluster_id": cluster_ids,
        }
    ).sort_values(["cluster_id", "feature"]).reset_index(drop=True)

    reps: list[str] = []
    for cluster_id, grp in cluster_df.groupby("cluster_id", sort=True):
        members = grp["feature"].tolist()
        chosen = None
        for candidate in PAPER_CLUSTER_REPRESENTATIVE_PRIORITY:
            if candidate in members:
                chosen = candidate
                break
        if chosen is None:
            mean_abs = pearson.loc[members, members].abs().mean(axis=1).sort_values(ascending=False)
            chosen = str(mean_abs.index[0])
        reps.append(chosen)

    exception_pair = {"Artery_Vessel_density", "Artery_Fractal_dimension"}
    if exception_pair.issubset(set(cols)):
        pair_corr = float(abs(pearson.loc["Artery_Vessel_density", "Artery_Fractal_dimension"]))
        if pair_corr >= PAPER_CLUSTER_THRESHOLD:
            for feat in sorted(exception_pair):
                if feat not in reps:
                    reps.append(feat)

    reps = [r for r in PAPER_CLUSTER_REPRESENTATIVE_PRIORITY if r in reps]
    return reps, pearson, cluster_df


def main() -> None:
    nh = pd.read_csv(NHANES_SOURCE)
    mac = pd.read_csv(MACULAR_SOURCE)
    px = pd.read_csv(PROXY_SOURCE)
    for part in (nh, mac, px):
        part["SEQN"] = pd.to_numeric(part["SEQN"], errors="coerce")
        part.dropna(subset=["SEQN"], inplace=True)
        part["SEQN"] = part["SEQN"].astype(int)
    mac = mac.drop_duplicates(subset=["SEQN"], keep="first").copy()
    px = px.drop_duplicates(subset=["SEQN"], keep="first").copy()
    df = nh.merge(mac, on="SEQN", how="inner").merge(px, on="SEQN", how="left")
    safe_write_csv(df, OUTPUT_DIR / "merged_full_global_only_source.csv")

    global_pruned_mediators, corr_log = build_global_pruned_mediators(df)
    paper_cluster_reps, pearson_corr, cluster_df = build_paper_cluster_branch(df)

    branch_specs = [
        ("sensitivity_cluster_representative", paper_cluster_reps),
    ]

    branch_manifest: dict[str, object] = {
        "source_csv": str(OUTPUT_DIR / "merged_full_global_only_source.csv"),
        "global_retinal_candidates": [c for c in GLOBAL_RETINAL_FEATURES if c in df.columns],
        "global_prune_corr_threshold": GLOBAL_PRUNE_CORR_THRESH,
        "global_prune_method": "spearman_only",
        "paper_cluster_threshold": PAPER_CLUSTER_THRESHOLD,
        "paper_cluster_features": [c for c in PAPER_CLUSTER_FEATURES if c in df.columns],
        "sensitivity_cluster_representative": paper_cluster_reps,
        "paper_cluster_count": int(cluster_df["cluster_id"].nunique()),
        "branches": [],
    }

    for tag, mediators in branch_specs:
        ready_df, role_map, transform_audit, all_nan_after = make_model_ready(df, mediators)
        csv_path = safe_write_csv(ready_df, OUTPUT_DIR / f"{tag}.csv")
        roles_path = safe_write_text(json.dumps(role_map, indent=2), OUTPUT_DIR / f"{tag}_roles.json")
        branch_manifest["branches"].append(
            {
                "tag": tag,
                "rows": int(len(ready_df)),
                "cols": int(len(ready_df.columns)),
                "mediator_count": int(len(role_map["mediators"])),
                "csv_path": str(csv_path),
                "roles_path": str(roles_path),
                "all_nan_dropped": all_nan_after,
                "transform_audit": transform_audit,
            }
        )

    safe_write_csv(cluster_df, DOCS_DIR / "paper_style_global_clusters.csv")
    safe_write_text(json.dumps(branch_manifest, indent=2), DOCS_DIR / "global_only_branch_manifest.json")
    safe_write_text(
        "\n".join(
            [
                "Global-only retinal workflow manifest",
                "=" * 50,
                "",
                "Paper-style cluster representative mediators:",
                *[f"- {c}" for c in paper_cluster_reps],
            ]
        ),
        DOCS_DIR / "global_only_branch_manifest.txt",
    )
    print("Built global-only branches.")


if __name__ == "__main__":
    main()
