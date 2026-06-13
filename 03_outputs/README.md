# Outputs

This folder contains the branch outputs created before model fitting.

## Files

- `sensitivity_cluster_representative.csv`
  - the primary role-locked cluster-global branch dataset

- `sensitivity_cluster_representative_roles.json`
  - the matching primary role file defining exposures, mediators, outcomes, covariates, and weight column

- `sensitivity_exposure_outcome_cluster_pruned.csv`
  - corrected stricter sensitivity branch dataset with pruned exposures, pruned outcomes, and cluster-representative retinal mediators

- `sensitivity_exposure_outcome_cluster_pruned_roles.json`
  - matching corrected stricter sensitivity role file

The canonical active branch data objects for this release are:

- `sensitivity_cluster_representative.*` for the primary paper branch
- `sensitivity_exposure_outcome_cluster_pruned.*` for the stricter secondary sensitivity branch
