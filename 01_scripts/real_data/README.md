# Real-Data Active Workflow

This subfolder contains the scripts used for the current primary branch and the retained sensitivity branch:

- `sensitivity_cluster_representative_gcovars_clean`
- `sensitivity_exposure_outcome_cluster_pruned`

## Primary branch sequence

1. `01_build_global_only_branches.py`
2. `02_run_global_only_comparisons.py`
3. `03_plot_global_only_comparison.py`
4. `05_plot_cluster_heatmaps.py`
5. `07_plot_branch_mediation_dashboard.py`
6. `08_plot_top_pathways_forest.py`

## Sensitivity branch sequences

1. `04_build_exposure_outcome_cluster_pruned_branch.py`
2. `06_run_exposure_outcome_cluster_pruned_comparison.py`
3. `05_plot_cluster_heatmaps.py`
4. `07_plot_branch_mediation_dashboard.py`
5. `08_plot_top_pathways_forest.py`

## Purpose of each script

- `01_build_global_only_branches.py`
  - builds the main global-only branches, including the cluster-representative mediator branch

- `02_run_global_only_comparisons.py`
  - runs `linear` and `RetiSEM_GAM` across the global-only branches

- `03_plot_global_only_comparison.py`
  - creates the global comparison figures and summary plots

- `04_build_exposure_outcome_cluster_pruned_branch.py`
  - creates the corrected stricter branch with pruned exposures, pruned outcomes, and cluster-representative retinal mediators

- `05_plot_cluster_heatmaps.py`
  - draws the retinal and exposure/outcome hierarchical heatmaps

- `06_run_exposure_outcome_cluster_pruned_comparison.py`
  - runs `linear` and `RetiSEM_GAM` for the corrected exposure/outcome plus cluster-retinal pruned branch

- `07_plot_branch_mediation_dashboard.py`
  - creates the branch summary dashboard figure

- `08_plot_top_pathways_forest.py`
  - creates the top-30 and all-pathway `TE`/`NDE`/`NIE` forest plots

- `run_realdata_linear_nonlinear_compare.py`
  - packaged final release runner used by the branch execution scripts; only `linear` and `RetiSEM_GAM` are kept here

- `_global_only_common.py`
  - shared constants, transforms, file paths, and helper functions used across the real-data release scripts
