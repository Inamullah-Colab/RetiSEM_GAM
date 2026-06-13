# Exposure/Outcome-Cluster-Pruned Branch Results

This folder contains the stricter secondary sensitivity-branch real-data results.

## Files

- `run_config.json`
  - exact settings used for the branch run
- `summary_compare.csv`
  - side-by-side branch summary for `linear` and `RetiSEM_GAM`
- `linear/`
  - linear mediation outputs
- `RetiSEM_GAM/`
  - non-linear GAM mediation outputs

## Interpretation

This branch keeps the same cluster-derived retinal mediator set as the main branch, but uses a narrower exposure and outcome search space.
