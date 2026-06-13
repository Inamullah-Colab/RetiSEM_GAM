# NHANES CVD/CAD Extension Scan Report

## Scope scanned
- Current analysis table: `sigma_style_table_all_models_with_bepag_q0p5.csv`
- Current reduced modeling data: `NHANES_final_causal_reduced.csv` (80 columns)
- Local merged NHANES pool: `NHANES_merged.csv`
- Local XPT modules found: `DEMO_D`, `BMX_D`, `BPX_D`, `HDL_D`, `TCHOL_D`, `TRIGLY_D`, `SLQ_D`, `SMQ_D`, `LEXABPI`

## Key finding
You already have a strong base for cardio-retinal causal modeling, but several high-value cardiovascular covariates are available locally and are currently not included in `NHANES_final_causal_reduced.csv`.

## High-priority variables available now (local files)
- Hemodynamics: `BPXSY2`, `BPXDI2`, `BPXSY3`, `BPXDI3`, `BPXSY4`, `BPXDI4`, `BPXCHR`
- Anthropometry: `BMXWAIST`, `BMXWT`
- Lipids/atherogenic risk: `LBXTR`, `LBDLDL`, `LBXAPB`
- Peripheral vascular disease marker: `LEXLABPI`, `LEXRABPI`
- Smoking exposure detail: `SMQ020`, `SMD030`, `SMD641`, `SMD650`
- Weights for MEC/lab analyses: `WTMEC2YR`, `WTSAF2YR`

## Derived variables to create (recommended)
- `SBP_mean`: mean of available `BPXSY1-4`
- `DBP_mean`: mean of available `BPXDI1-4`
- `PulsePressure_mean`: `SBP_mean - DBP_mean`
- `MAP_mean`: `DBP_mean + (SBP_mean-DBP_mean)/3`
- `WaistHeightRatio`: `BMXWAIST / BMXHT`
- `NonHDL_C`: `LBXTC - LBDHDD`

## Important variables not in local files (download next)
- Glycemia: fasting glucose (`GLU_*`), HbA1c (`GHB_*`), fasting insulin (`INS_*`)
- Inflammation: CRP (`CRP_*`, `LBXCRP`)
- Kidney risk: creatinine / eGFR (`BIOPRO_*`), urine albumin+creatinine (`ALB_CR_*`)
- CAD outcomes/comorbidity: MCQ cardiovascular history (`MCQ_*`), diabetes diagnosis (`DIQ_*`), BP/cholesterol treatment (`BPQ_*`)
- Mortality linkage for hard outcomes: NHANES linked mortality files

## Latent blocks for BEPAG-SEM/SIGMA-style modeling
- Hemodynamic load: `SBP_mean`, `DBP_mean`, `PulsePressure_mean`, `BPXPLS`
- Metabolic-atherogenic burden: `LBXTC`, `LBDHDD`, `LBXTR`, `LBDLDL`, `NonHDL_C`, `LBXAPB`
- Adiposity-body composition: `BMXBMI`, `BMXWAIST`, `WaistHeightRatio`
- Tobacco exposure: `SMQ020`, `SMD030`, `SMD641`, `SMD650`
- Peripheral vascular health: `LEXLABPI`, `LEXRABPI`

## Output files added in this step
- `nhanes_cvd_extension_variable_map.csv`
- `prepare_extension_dataset_template.py`
- `NHANES_CVD_EXTENSION_SCAN_REPORT.md` (this file)

## Notes
- Existing files are untouched.
- This is a planning + template stage for later controlled integration.
