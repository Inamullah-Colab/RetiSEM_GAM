# Results

This folder contains the main branch model outputs.

## Primary result folder

- `sensitivity_cluster_representative_gcovars_clean/`

This folder contains:

- `linear/`
- `RetiSEM_GAM/`
- `run_config.json`
- `summary_compare.csv`

Within each model subfolder:

- `summary.csv`
  - per-model branch summary
- `compact_effect_summary.csv`
  - compact pathway-level summary used for downstream dashboards and forest plots
- `mediation_table_all_combos.csv`
  - combined full pathway table for that model and branch
- `mediation_table_<MODEL>_<EXPOSURE>_<OUTCOME>.csv`
  - exposure-outcome specific pathway tables

## Primary summary

Current branch-level summary:

- `linear`: 273 pathways, 10 significant NIE
- `RetiSEM_GAM`: 273 pathways, 10 significant NIE

## Stricter clustered sensitivity branch

- `sensitivity_exposure_outcome_cluster_pruned/`

Summary:

- `linear`: 154 pathways, 8 significant NIE
- `RetiSEM_GAM`: 154 pathways, 4 significant NIE

This stricter branch combines:

- pruned exposures
- pruned outcomes
- cluster-representative retinal mediators
- `Z = 5`
- `G = 4`

## Reading guide

For most users, start with:

- `summary_compare.csv`
- `linear/compact_effect_summary.csv`
- `RetiSEM_GAM/compact_effect_summary.csv`
