# Scripts

This folder contains the active real-data scripts and the upstream synthetic/GAM-SEM reference scripts.

## `real_data`

This is the active branch workflow.

Main files:

- `01_build_global_only_branches.py`
- `02_run_global_only_comparisons.py`
- `03_plot_global_only_comparison.py`
- `04_build_exposure_outcome_cluster_pruned_branch.py`
- `05_plot_cluster_heatmaps.py`
- `06_run_exposure_outcome_cluster_pruned_comparison.py`
- `07_plot_branch_mediation_dashboard.py`
- `08_plot_top_pathways_forest.py`
- `run_realdata_linear_nonlinear_compare.py`
- `_global_only_common.py`

Active execution order:

1. build the primary cluster-representative retinal branch
2. run `linear` and `RetiSEM_GAM` on the primary branch
3. build the stricter exposure/outcome-cluster-pruned sensitivity branch
4. run `linear` and `RetiSEM_GAM` on the stricter sensitivity branch
5. generate clustering plots
6. generate dashboard plots
7. generate pathway forest plots

## `synthetic_reference`

This folder contains copied upstream scripts that document how the synthetic benchmark and GAM-SEM implementation were structured in the original `retisem_workspace`.

These files are included for:

- algorithm traceability
- GitHub method transparency
