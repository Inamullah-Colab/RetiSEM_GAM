# Source Provenance

This folder was added to make the standalone release package traceable back to the older `NAHES_Dataset` workspace.

It does not replace the active BC workflow. It documents where the current merged inputs came from.

## Structure

### `legacy_nhanes_xpt/`

Selected raw NHANES source tables copied from the older `New folder/NAHES_Dataset` workspace.

These are the main files that feed the active phenotype domains used in the final branch:

- `DEMO_D.xpt`
  - age, sex, ethnicity, education, poverty ratio, survey weights
- `BPX_D.xpt`
  - blood pressure outcomes
- `BPQ_D.xpt`
  - blood pressure questionnaire support variables
- `BMX_D.xpt`
  - body measurements
- `TRIGLY_D.xpt`
  - triglycerides, including `LBXTR`
- `TCHOL_D.xpt`
  - total cholesterol reference domain
- `HDL_D.xpt`
  - HDL lipid reference domain
- `GLU_D.xpt`
  - fasting glucose, including `LBXGLU`
- `GHB_D.xpt`
  - glycohemoglobin, including `LBXGH`
- `CRP_D.xpt`
  - C-reactive protein, including `LBXCRP`
- `BIOPRO_D.xpt`
  - apolipoprotein / clinical chemistry variables including `LBXAPB`, insulin, creatinine
- `ALB_CR_D.xpt`
  - urine albumin and urine creatinine variables including `URXUMA`, `URXUCR`
- `LEXABPI.xpt`
  - ankle-brachial pressure index reference domain
- `DIQ_D.xpt`
  - diabetes questionnaire domain
- `MCQ_D.xpt`
  - medical conditions domain
- `SMQ_D.xpt`
  - smoking domain
- `SLQ_D.xpt`
  - sleep domain

### `historical_reports/`

Key legacy reports from the earlier NHANES workflow.

Important:

- these are archival reports only
- they should not be read as the active release specification
- if they differ from the current release docs, the current release docs take precedence

These are included for:

- audit trail
- variable-history lookup
- paper writing support
- GitHub documentation support

The archival reports are mainly useful for understanding how some merged or derived quantities were documented historically, for example:

- matched NHANES-retinal tables
- older derived hemodynamic summaries such as `SBP_mean`, `DBP_mean`, `PulsePressure_mean`, `MAP_mean`
- older cardiovascular variable extension notes
- earlier pruning summaries

This subfolder also includes the original proxy-genetic construction references:

- `REFERENCE_1000G_PROXY_ASSUMPTIONS.txt`
- `reference_1000g_proxy_mapping.csv`

### `historical_scripts/`

Selected historical scripts that show how the older NHANES dataset was originally read, merged, extended, and converted into model-ready tables.

These are reference scripts only. They are not the active final branch pipeline.

Also see:

- `HISTORICAL_WORKSPACE_INDEX.md`
  - explains the major old `NAHES_Dataset` subfolders and why they were not copied wholesale
- `historical_reports/README.md`
  - explains how to interpret the archived reports safely

## Active Branch Mapping

The active release branches are now:

- `03_outputs/sensitivity_cluster_representative.csv`
- `03_outputs/sensitivity_exposure_outcome_cluster_pruned.csv`

with roles defined in:

- `03_outputs/sensitivity_cluster_representative_roles.json`
- `03_outputs/sensitivity_exposure_outcome_cluster_pruned_roles.json`

The mapping from final active variables back to raw domains is:

- exposures
  - `LBXTR` -> `TRIGLY_D.xpt`
  - `LBXAPB` -> `BIOPRO_D.xpt`
- outcomes
  - `BPXSY2`, `BPXDI2`, `BPXSY4`, `BPXDI4` -> `BPX_D.xpt`
  - `LBXGLU` -> `GLU_D.xpt`
  - `LBXGH` -> `GHB_D.xpt`
  - `LBXIN`, `LBXSCR`, `LBXAPB` -> `BIOPRO_D.xpt`
  - `LBXCRP` -> `CRP_D.xpt`
  - `URXUMA`, `URXUCR` -> `ALB_CR_D.xpt`
- Z covariates
  - `RIDAGEYR`, `RIAGENDR`, `RIDRETH1`, `INDFMPIR`, `DMDEDUC3`, `WTMEC2YR` -> `DEMO_D.xpt`
- G covariates
  - `GREF_AMR`, `GREF_EUR`, `GREF_SAS`, `GREF_entropy` -> `proxy_genetics_for_merge.csv`
- mediators
  - retinal global features -> `macular_bc_prepared_with_seq.csv`

## Interpretation

This means the release package now contains both:

- the active merged CSV tables needed to rerun the final BC analysis
- the upstream raw-domain provenance needed to explain where the NHANES variables originally came from

For the proxy-genetic construction details specifically, see:

- `../../04_docs/GENETIC_PROXY_METHOD.md`
