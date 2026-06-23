# RetiSEM-GAM GitHub Release
<p align="center">
  <img src="ig_0b1943f95346f242016a3a8079c4a48191acac04af4dc9afbe.png" alt="RetiSEM_GAM visual" width="100%">
</p>
This folder is a standalone GitHub-facing release package for the current global-retinal cluster branch of the project.
![model](https://img.shields.io/badge/model-RetiSEM_GAM-1f6feb)
![python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![method](https://img.shields.io/badge/method-GAM%20%2B%20SEM-0A7E8C)
![domain](https://img.shields.io/badge/domain-retinal%20features-2E8B57)
![focus](https://img.shields.io/badge/focus-eye%20to%20heart%20pathways-C0392B)
![workflow](https://img.shields.io/badge/workflow-hypothesis%20generation-black?logo=github)

This GitHub-facing package intentionally excludes the internal manuscript workspace.

## Repository Purpose

This repository exposes the current public release of the project in a compact reproducible form.

Main method:

- `RetiSEM_GAM`

Baseline comparator:

- `linear`

Primary analysis branch:

- `sensitivity_cluster_representative_gcovars_clean`

Secondary sensitivity branch:

- `sensitivity_exposure_outcome_cluster_pruned`

## Quick Start

1. Create a Python environment and install the core packages:
   - `pip install -r requirements.txt`
2. Run the primary public workflow:
   - `python run_primary_release.py`
3. Optionally include the stricter sensitivity branch:
   - `python run_primary_release.py --with-sensitivity`

Windows shortcut:

- `run_primary_release.bat`

Main outputs to inspect after the run:

- `05_results/sensitivity_cluster_representative_gcovars_clean/summary_compare.csv`
- `06_plots/global_retinal_cluster_heatmap.png`
- `06_plots/forest_top30_linear_cluster_representative.png`
- `06_plots/forest_top30_gam_cluster_representative.png`

The goal of this release is to keep everything for the current `sensitivity_cluster_representative_gcovars_clean` workflow in one synchronized place:

- raw input files used in this workflow
- selected legacy NHANES raw-domain source files for provenance
- reviewer-friendly sample data
- real-data scripts for the active branch
- upstream synthetic and GAM-SEM reference code
- cleaned outputs
- final model results
- paper figures
- dependency files and documentation

## Active Analysis Scope

This release now treats one branch as primary:

- `sensitivity_cluster_representative_gcovars_clean`

This primary branch uses:

- cluster-derived global retinal mediators
- full retained lipid exposure block
- retained cardiometabolic / renal / inflammatory outcome block
- `linear` and `RetiSEM_GAM` comparisons

The stricter retained sensitivity branch is:

- `sensitivity_exposure_outcome_cluster_pruned`

This branch combines pruned exposures, pruned outcomes, and cluster-representative retinal mediators.

Older fixed-panel branches are not part of the cleaned release package.

## Folder Sequence

### `00_inputs`

Contains:

- `raw_main/`
  - raw source tables used in the active workflow
- `source_provenance/`
  - selected historical NHANES XPT files, reports, and merge scripts copied from the older `NAHES_Dataset` workspace
- `sample_small/`
  - small reviewer/editor sample files that can be run or inspected without the full datasets

### `01_scripts`

Contains:

- `real_data/`
  - the active real-data pipeline scripts
- `synthetic_reference/`
  - synthetic benchmark and GAM-SEM reference scripts copied from the upstream `retisem_workspace`

### `02_model_reference`

Contains:

- `upstream_gam_sem_code/`
  - upstream RetiSEM / GAM-SEM implementation references used to avoid ambiguity in formulation and algorithm description

### `03_outputs`

Contains:

- the primary cluster-representative branch dataset and role-lock file
- the stricter clustered sensitivity branch dataset

### `04_docs`

Contains:

- workflow sequence
- input documentation
- reviewer/sample-data notes
- method-reference notes

### `05_results`

Contains:

- the primary cluster-representative `linear` and `RetiSEM_GAM` results
- branch summary tables and pathway outputs

### `06_plots`

Contains:

- cluster-global branch clustering and forest plots
- secondary sensitivity plots for the clustered-pruned branch

## Recommended Reading Order

1. this `README.md`
2. [`REVIEWER_AUDIT_TRAIL.md`](./REVIEWER_AUDIT_TRAIL.md)
3. [`04_docs/PROJECT_SEQUENCE.md`](./04_docs/PROJECT_SEQUENCE.md)
4. [`00_inputs/README.md`](./00_inputs/README.md)
5. [`04_docs/DATASET_SOURCE_REFERENCE.md`](./04_docs/DATASET_SOURCE_REFERENCE.md)
6. [`04_docs/DATA_PROVENANCE_MAP.md`](./04_docs/DATA_PROVENANCE_MAP.md)
7. [`04_docs/RETINAL_SOURCE_PROVENANCE.md`](./04_docs/RETINAL_SOURCE_PROVENANCE.md)
8. [`04_docs/SYNTHETIC_AND_MODEL_REFERENCE.md`](./04_docs/SYNTHETIC_AND_MODEL_REFERENCE.md)
9. [`04_docs/BRANCH_SELECTION_FOR_PAPER.md`](./04_docs/BRANCH_SELECTION_FOR_PAPER.md)
10. [`04_docs/GENETIC_PROXY_METHOD.md`](./04_docs/GENETIC_PROXY_METHOD.md)
11. [`01_scripts/README.md`](./01_scripts/README.md)
12. [`02_model_reference/README.md`](./02_model_reference/README.md)
13. [`03_outputs/README.md`](./03_outputs/README.md)
14. [`05_results/README.md`](./05_results/README.md)
15. [`06_plots/README.md`](./06_plots/README.md)

## Primary Files

Active branch data:

- `03_outputs/sensitivity_cluster_representative.csv`
- `03_outputs/sensitivity_cluster_representative_roles.json`

Active branch results:

- `05_results/sensitivity_cluster_representative_gcovars_clean/summary_compare.csv`

Active branch figures:

- `06_plots/global_retinal_cluster_heatmap.png`
- `06_plots/forest_top30_linear_cluster_representative.png`
- `06_plots/forest_top30_gam_cluster_representative.png`

## Reviewer / Editor Convenience

The folder `00_inputs/sample_small/` contains 50-row sample files so a reviewer or editor can inspect the structure of the workflow without needing to load the full raw inputs.

The folder `00_inputs/source_provenance/` now also preserves the main raw NHANES domain files and historical documentation from the older `NAHES_Dataset` workspace.

The folder `07_reviewer_demo/` provides a reviewer-facing smoke test, an exact primary-branch reproduction entry point, and bundled expected result snapshots.

For documentation, use:

- `REVIEWER_AUDIT_TRAIL.md`
  - end-to-end audit map
- `04_docs/DATASET_SOURCE_REFERENCE.md`
  - dataset descriptions and source links
- `04_docs/RETINAL_SOURCE_PROVENANCE.md`
  - retinal-source provenance and matching path
- `04_docs/GENETIC_PROXY_METHOD.md`
  - proxy-genetic covariate construction and interpretation
- `04_docs/SYNTHETIC_AND_MODEL_REFERENCE.md`
  - synthetic benchmark and upstream model-reference layer

## Dependencies

See:

- [`requirements.txt`](./requirements.txt)
- [`requirements-optional.txt`](./requirements-optional.txt)
- [`LICENSE`](./LICENSE)

Interpretation:

- `requirements.txt`
  - packages needed for the active release workflow, plotting, and shipped provenance helpers
- `requirements-optional.txt`
  - extra packages for older synthetic benchmark baselines and extended causal-discovery comparisons such as LiNGAM, DAGMA, NOTEARS, DECI, and tree-based baselines

## Important Note

This release folder is intentionally separate from the earlier workspace to avoid mixing:

- archived branches
- exploratory variants
- unrelated legacy outputs

It should be treated as the clean release package for the active cluster-global branch analysis, with the clustered-pruned branch retained as the stricter sensitivity branch.
