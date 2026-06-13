from __future__ import annotations

import json

import pandas as pd

from _global_only_common import (
    DOCS_DIR,
    OUTPUT_DIR,
    make_model_ready,
    safe_write_csv,
    safe_write_text,
)


PRUNED_EXPOSURES = ["LBXTR", "LBXAPB"]
PRUNED_OUTCOMES = [
    "BPXSY2",
    "BPXDI2",
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

CLUSTER_ROLE_FILE = OUTPUT_DIR / "sensitivity_cluster_representative_roles.json"
OUTPUT_TAG = "sensitivity_exposure_outcome_cluster_pruned"


def main() -> None:
    df = pd.read_csv(OUTPUT_DIR / "merged_full_global_only_source.csv")
    cluster_roles = json.loads(CLUSTER_ROLE_FILE.read_text(encoding="utf-8"))
    cluster_mediators = cluster_roles["mediators"]

    ready_df, role_map, transform_audit, all_nan_after = make_model_ready(df, cluster_mediators)
    role_map["exposures"] = [c for c in PRUNED_EXPOSURES if c in ready_df.columns]
    role_map["outcomes"] = [c for c in PRUNED_OUTCOMES if c in ready_df.columns]

    base_cols = [c for c in ["SEQN", "Name"] if c in ready_df.columns]
    keep_cols = base_cols + role_map["exposures"] + role_map["outcomes"] + role_map["mediators"]
    keep_cols += [c for c in role_map["covars"] if c not in keep_cols]
    keep_cols += [c for c in role_map["weights"] if c not in keep_cols]
    ready_df = ready_df[keep_cols].copy()

    csv_path = safe_write_csv(ready_df, OUTPUT_DIR / f"{OUTPUT_TAG}.csv")
    roles_path = safe_write_text(json.dumps(role_map, indent=2), OUTPUT_DIR / f"{OUTPUT_TAG}_roles.json")
    summary = {
        "rows": int(len(ready_df)),
        "cols": int(len(ready_df.columns)),
        "exposures": role_map["exposures"],
        "outcomes": role_map["outcomes"],
        "mediators": role_map["mediators"],
        "covars": role_map["covars"],
        "z_covars": role_map["z_covars"],
        "g_covars": role_map["g_covars"],
        "all_nan_dropped": all_nan_after,
        "transform_audit": transform_audit,
        "source_cluster_role_file": str(CLUSTER_ROLE_FILE),
        "csv_path": str(csv_path),
        "roles_path": str(roles_path),
    }
    safe_write_text(json.dumps(summary, indent=2), DOCS_DIR / f"{OUTPUT_TAG}_summary.json")
    safe_write_text(
        "\n".join(
            [
                "Exposure/outcome-cluster-pruned sensitivity branch",
                "=" * 60,
                f"Rows: {summary['rows']}",
                f"Columns: {summary['cols']}",
                "",
                "Pruned exposures:",
                *[f"- {c}" for c in summary["exposures"]],
                "",
                "Pruned outcomes:",
                *[f"- {c}" for c in summary["outcomes"]],
                "",
                "Cluster-representative retinal mediators:",
                *[f"- {c}" for c in summary["mediators"]],
                "",
                f"Z covariates: {len(summary['z_covars'])}",
                f"G covariates: {len(summary['g_covars'])}",
            ]
        ),
        DOCS_DIR / f"{OUTPUT_TAG}_summary.txt",
    )
    print(csv_path)
    print(roles_path)


if __name__ == "__main__":
    main()
