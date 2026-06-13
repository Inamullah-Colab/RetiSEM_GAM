# Raw Main Inputs

This folder contains the main CSV inputs used by the active release workflow.

## Files

- `nhanes_core_for_merge.csv`
  - main NHANES-derived systemic phenotype table used for exposure, outcome, and covariate assembly
- `macular_bc_prepared_with_seq.csv`
  - prepared global retinal biomarker table from the macular BC workflow
- `proxy_genetics_for_merge.csv`
  - ancestry-style proxy covariate table used as the `G` adjustment block
- `nhanes_macular_proxy_merged.csv`
  - merged reference table retained for traceability and audit support

## Role in the workflow

These files are used upstream of:

- `01_scripts/real_data/01_build_global_only_branches.py`
- `01_scripts/real_data/04_build_exposure_outcome_cluster_pruned_branch.py`

They are not the final model-ready branch tables. Those are written into:

- `03_outputs/sensitivity_cluster_representative.csv`
- `03_outputs/sensitivity_exposure_outcome_cluster_pruned.csv`

## Important reviewer clarification

This folder contains the prepared tables actually used by the active release workflow.

That means:

- NHANES-derived systemic variables are present here as assembled CSV inputs
- retinal mediators are present here as a prepared retinal feature table
- proxy-genetic covariates are present here as a prepared adjustment table

This folder does not by itself provide:

- the full raw-image retinal acquisition workflow
- a full rerunnable image-to-feature retinal extraction pipeline
- a direct APTOS acquisition rerun inside this release package

So reviewers can audit the released analysis inputs and rerun the released models, but not reconstruct the entire upstream retinal image engineering stack from this folder alone.

For the retinal-source audit note that ties together the shipped prepared table, the historical `Name -> SEQN` matching script, and the downstream pruning logic, use:

- `../../04_docs/RETINAL_SOURCE_PROVENANCE.md`
