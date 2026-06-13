# Historical Reports

This folder contains selected archival reports copied from earlier NHANES workspace stages.

## Important status

These files are:

- archival provenance material
- variable-history references
- older workflow notes

These files are not:

- the active release workflow
- the final paper-facing branch definition
- the authoritative source for the shipped `03_outputs/`, `05_results/`, or `06_plots/` files

## How to use this folder

Use these reports only for:

- tracing where older variables and intermediate datasets came from
- understanding earlier preprocessing and merge steps
- checking historical assumptions behind retained provenance assets

## Files intentionally kept

- `FULL_PROJECT_REPORT_START_TO_END.md`
  - broad end-to-end historical workflow summary
- `NHANES_CVD_EXTENSION_SCAN_REPORT.md`
  - historical note on expanded cardiovascular variable coverage and derived-variable suggestions
- `MODEL_READY_CONSERVATIVE_CORELOCKED_SUMMARY.txt`
  - compact historical pruning summary
- `REFERENCE_1000G_PROXY_ASSUMPTIONS.txt`
  - historical proxy-genetic assumptions
- `reference_1000g_proxy_mapping.csv`
  - historical proxy-genetic mapping table

## What these archival reports help explain

These reports help explain older generation or documentation of:

- assembled NHANES phenotype tables
- matched NHANES-retinal tables
- historical derived variables such as `SBP_mean`, `DBP_mean`, `PulsePressure_mean`, `MAP_mean`, and `NonHDL_C`
- earlier variable-screening and pruning decisions

They do not define the final active release branch by themselves.

Do not use these reports as the primary explanation of the current release.

## Current authoritative release files

For the active GitHub release, use:

- `REVIEWER_AUDIT_TRAIL.md`
- `04_docs/DATASET_SOURCE_REFERENCE.md`
- `04_docs/DATA_PROVENANCE_MAP.md`
- `04_docs/RETINAL_SOURCE_PROVENANCE.md`
- `04_docs/GENETIC_PROXY_METHOD.md`
- `04_docs/SYNTHETIC_AND_MODEL_REFERENCE.md`
- `03_outputs/`
- `05_results/`
- `06_plots/`

## Practical interpretation

If a historical report conflicts in wording, scope, or branch naming with the active release docs, follow the active release docs.
