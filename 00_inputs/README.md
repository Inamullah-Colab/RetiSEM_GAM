# Inputs

This folder contains the active workflow inputs, a small reviewer package, and a raw-source provenance bundle taken from the older `NAHES_Dataset` workspace.

## `raw_main`

These are the main source files used in the active branch:

- `nhanes_core_for_merge.csv`
  - NHANES-derived phenotype table including blood pressure, renal, glycemic, inflammatory, and other systemic variables used in the workflow

- `macular_bc_prepared_with_seq.csv`
  - retinal biomarker source table

- `proxy_genetics_for_merge.csv`
  - proxy-genetic covariate source table

- `nhanes_macular_proxy_merged.csv`
  - previously merged reference table retained for traceability

Use:

- [`raw_main/README.md`](./raw_main/README.md)

## `source_provenance`

This folder was added so the release package also contains the older NHANES raw-source context that was still missing.

It includes:

- `legacy_nhanes_xpt/`
  - selected original NHANES XPT tables for the exposure, outcome, covariate, and clinical domains
- `historical_reports/`
  - older workflow reports and documentation files
- `historical_scripts/`
  - older NHANES merge / build scripts for provenance

Use:

- [`source_provenance/README.md`](./source_provenance/README.md)

## `sample_small`

This folder contains 50-row samples of the raw source tables and of the final active branch dataset.

Current sample files:

- `macular_bc_prepared_with_seq_sample50.csv`
- `nhanes_core_for_merge_sample50.csv`
- `nhanes_macular_proxy_merged_sample50.csv`
- `proxy_genetics_for_merge_sample50.csv`
- `sensitivity_cluster_representative_sample50.csv`
- `sensitivity_exposure_outcome_cluster_pruned_sample50.csv`

These are intended for:

- GitHub demonstration
- reviewer/editor inspection
- quick sanity checks without loading the full raw inputs

Use:

- [`sample_small/README.md`](./sample_small/README.md)
