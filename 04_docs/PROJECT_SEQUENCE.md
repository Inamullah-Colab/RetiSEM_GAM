# Project Sequence

This file gives the exact sequence for the standalone release folder.

## 1. Inspect the inputs

Start in:

- `00_inputs/raw_main/`
- `00_inputs/source_provenance/`
- `00_inputs/sample_small/`

The raw files show the source tables used in the active branch.
The sample files provide lightweight reviewer-friendly inspection data.
The provenance folder shows where the NHANES domains originally came from in the older workspace.

## 2. Understand the current real-data pipeline

Read:

- `01_scripts/real_data/README.md`
- `04_docs/BRANCH_SELECTION_FOR_PAPER.md`

Then follow the primary run order:

1. `01_build_global_only_branches.py`
2. `02_run_global_only_comparisons.py`
3. `03_plot_global_only_comparison.py`
4. `05_plot_cluster_heatmaps.py`
5. `07_plot_branch_mediation_dashboard.py`
6. `08_plot_top_pathways_forest.py`

## 3. Inspect the upstream model reference

Read:

- `02_model_reference/README.md`

This connects the release package back to the original `retisem_workspace` synthetic and GAM-SEM implementation logic.

## 4. Inspect the primary branch outputs

Use:

- `03_outputs/sensitivity_cluster_representative.csv`
- `03_outputs/sensitivity_cluster_representative_roles.json`

## 5. Inspect the primary model results

Use:

- `05_results/sensitivity_cluster_representative_gcovars_clean/summary_compare.csv`

This is the main branch-level comparison for:

- `linear`
- `RetiSEM_GAM`

## 6. Inspect the main figures

Use:

- `06_plots/global_retinal_cluster_heatmap.png`
- `06_plots/forest_top30_linear_cluster_representative.png`
- `06_plots/forest_top30_gam_cluster_representative.png`

## 7. Important release interpretation

This standalone folder should now be read as:

1. active cluster-global BC branch inputs and outputs
2. upstream RetiSEM / GAM-SEM model reference
3. historical NHANES provenance copied from the older `NAHES_Dataset`
4. a GitHub-facing release package in which the cluster-representative branch is the main analysis and the exposure/outcome-pruned branch is secondary sensitivity only

This avoids losing the original raw NHANES context while still keeping the active final branch separate from older exploratory work.
