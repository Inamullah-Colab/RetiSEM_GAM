# Full Project Report (Start to Finish)

## 1) Project Goal
Build a clean, analysis-ready NHANES causal dataset, integrate retinal features, reduce multicollinearity, and run mediation + IV effect estimation with publication-style outputs.

## 2) End-to-End Timeline of What You Did

### Step A: Raw NHANES ingestion and merge
- Loaded NHANES `.xpt` source files (demographics, blood pressure, body measures, sleep, smoking, lipids, ABI, etc.).
- Merged all datasets by participant ID (`SEQN`).
- Main script: `NAHES_Dataset/merge_nhanes.py`
- Output:
- `NAHES_Dataset/NHANES_merged.csv` (`10,348 x 187`)
- `NAHES_Dataset/NHANES_merge_summary.txt`

### Step B: Causal cohort selection
- Defined key causal variables and kept participants with complete key-variable data.
- This reduced sample size due to missingness in key measures (especially BP).
- Output:
- `NAHES_Dataset/NHANES_cleaned_causal.csv` (`6,606 x 187`)
- `NAHES_Dataset/NHANES_cleaning_summary.txt`

### Step C: Missing-data filtering and imputation
- Applied missingness threshold rule: removed variables with `>30%` missing.
- Removed `87` variables and retained `100` variables.
- Imputed remaining missing values:
- Numeric: median imputation
- Non-numeric: mode imputation
- Achieved `0` missing values in final causal dataset.
- Main scripts:
- `NAHES_Dataset/impute_data.py`
- `NAHES_Dataset/finalize_data.py`
- Outputs:
- `NAHES_Dataset/NHANES_final_causal.csv` (`6,606 x 100`)
- `NAHES_Dataset/NHANES_imputation_summary.txt`
- `NAHES_Dataset/NHANES_final_summary.txt`

### Step D: Multicollinearity diagnostics and reduction
- Ran correlation and VIF diagnostics.
- Generated full and key-variable heatmaps.
- Removed redundant variables with high collinearity.
- Kept key causal variables while reducing feature redundancy.
- Main scripts:
- `NAHES_Dataset/multicollinearity_analysis.py`
- `NAHES_Dataset/create_reduced_dataset.py`
- Outputs:
- `NAHES_Dataset/NHANES_final_causal_reduced.csv` (`6,606 x 80`) (recommended modeling file)
- `NAHES_Dataset/correlation_heatmap_full.png`
- `NAHES_Dataset/correlation_heatmap_key_variables.png`
- `NAHES_Dataset/MULTICOLLINEARITY_ANALYSIS.txt`

### Step E: Retinal dataset preparation and VIF-based retinal reduction
- Processed and imputed retinal measurements.
- Ran VIF-based reduction on retinal features (`VIF > 10` removal).
- Script used:
- `NAHES_Dataset/vif_check_and_reduce_macular.py`
- Outputs:
- `NAHES_Dataset/Macular_Zone_B_Measurement_imputed.csv` (`4,055 x 31`)
- `NAHES_Dataset/Macular_Zone_B_Measurement_imputed_reduced.csv` (`4,055 x 6`)
- Retained reduced retinal variables:
- `Name`
- `Squared_curvature_tortuosity`
- `Artery_Distance_tortuosity`
- `Artery_Squared_curvature_tortuosity`
- `Vein_Distance_tortuosity`
- `Vein_Squared_curvature_tortuosity`

### Step F: NHANES + retina integration
- Linked retinal records to NHANES (via ID mapping/sequence workflow).
- Produced a combined analysis table for mediation.
- Output:
- `NAHES_Dataset/NHANES_final_with_retina.csv` (`4,055 x 86`)

### Step G: Mediation and IV analysis (initial run)
- Ran multi-mediator mediation with:
- 5 retinal mediators
- bootstrap = `1000`
- outcomes: `BPXSY1`, `BPXDI1`
- IV comparison via 2SLS with instrument `SMDUPCA`
- Script:
- `NAHES_Dataset/mediation_iv_multi.py`
- Outputs included:
- `NAHES_Dataset/mediation_multimed_BPXSY1.csv`
- `NAHES_Dataset/mediation_multimed_BPXDI1.csv`
- `NAHES_Dataset/iv_comparison_BPXSY1.csv`
- `NAHES_Dataset/iv_comparison_BPXDI1.csv`
- `NAHES_Dataset/indirect_effects_BPXSY1.png`
- `NAHES_Dataset/indirect_effects_BPXDI1.png`
- `NAHES_Dataset/mediation_models_BPXSY1.txt`
- `NAHES_Dataset/mediation_models_BPXDI1.txt`

### Step H: Paper-style output upgrade (table + forest plot format)
- Updated mediation script to export publication-style columns:
- `Pathway`
- `TE_Estimate`, `TE_CI_Lower`, `TE_CI_Upper`
- `NDE_Estimate`, `NDE_CI_Lower`, `NDE_CI_Upper`
- `NIE_Estimate`, `NIE_CI_Lower`, `NIE_CI_Upper`
- Added forest plot matching requested style.
- New outputs:
- `NAHES_Dataset/mediation_table_hpp_style_BPXSY1.csv`
- `NAHES_Dataset/mediation_table_hpp_style_BPXDI1.csv`
- `NAHES_Dataset/forest_hpp_style_BPXSY1.png`
- `NAHES_Dataset/forest_hpp_style_BPXDI1.png`

### Step I: Better/different final upgrade
- Enhanced `NAHES_Dataset/mediation_iv_multi.py` further:
- Runs both exposures: `LBXTC` and `LBDHDD`
- Keeps `1000` bootstrap and IV-2SLS
- Adds rounded tables for direct manuscript use
- Adds `NIE_Significant` flag
- Adds second visualization (`effect_triplets`)
- Adds cross-model overview summary
- New outputs:
- `NAHES_Dataset/mediation_table_hpp_style_LBXTC_BPXSY1.csv`
- `NAHES_Dataset/mediation_table_hpp_style_LBXTC_BPXSY1_rounded.csv`
- `NAHES_Dataset/mediation_table_hpp_style_LBXTC_BPXDI1.csv`
- `NAHES_Dataset/mediation_table_hpp_style_LBXTC_BPXDI1_rounded.csv`
- `NAHES_Dataset/mediation_table_hpp_style_LBDHDD_BPXSY1.csv`
- `NAHES_Dataset/mediation_table_hpp_style_LBDHDD_BPXSY1_rounded.csv`
- `NAHES_Dataset/mediation_table_hpp_style_LBDHDD_BPXDI1.csv`
- `NAHES_Dataset/mediation_table_hpp_style_LBDHDD_BPXDI1_rounded.csv`
- `NAHES_Dataset/forest_hpp_style_LBXTC_BPXSY1.png`
- `NAHES_Dataset/forest_hpp_style_LBXTC_BPXDI1.png`
- `NAHES_Dataset/forest_hpp_style_LBDHDD_BPXSY1.png`
- `NAHES_Dataset/forest_hpp_style_LBDHDD_BPXDI1.png`
- `NAHES_Dataset/effect_triplets_LBXTC_BPXSY1.png`
- `NAHES_Dataset/effect_triplets_LBXTC_BPXDI1.png`
- `NAHES_Dataset/effect_triplets_LBDHDD_BPXSY1.png`
- `NAHES_Dataset/effect_triplets_LBDHDD_BPXDI1.png`
- `NAHES_Dataset/mediation_overview_all_models.csv`

## 3) Current Core Datasets (Latest)
- `NAHES_Dataset/NHANES_final_causal.csv`: `6,606 x 100`
- `NAHES_Dataset/NHANES_final_causal_reduced.csv`: `6,606 x 80`
- `NAHES_Dataset/NHANES_final_with_retina.csv`: `4,055 x 86`
- `NAHES_Dataset/Macular_Zone_B_Measurement_imputed_reduced.csv`: `4,055 x 6`

## 4) Latest High-Level Mediation/IV Summary
From `NAHES_Dataset/mediation_overview_all_models.csv`:
- `LBXTC -> BPXSY1`: TE `0.0230` (95% CI: `0.0072, 0.0392`), IV total `0.0409`
- `LBXTC -> BPXDI1`: TE `0.0625` (95% CI: `0.0495, 0.0759`), IV total `0.0458`
- `LBDHDD -> BPXSY1`: TE `0.0234` (95% CI: `-0.0230, 0.0675`), IV total `0.0793`
- `LBDHDD -> BPXDI1`: TE `0.0404` (95% CI: `-0.0028, 0.0821`), IV total `0.0609`

## 5) Key Final Deliverables You Produced
- Clean, complete NHANES causal dataset with no missing values.
- Reduced causal dataset with lower multicollinearity.
- Reduced retinal mediator set after VIF filtering.
- Integrated NHANES-retina analysis dataset.
- Multi-mediator bootstrap mediation + IV comparison outputs.
- Publication-style mediation tables and forest/comparison plots.

## 6) Recommended Files for Writing/Submission
- Main analysis data:
- `NAHES_Dataset/NHANES_final_with_retina.csv`
- Manuscript tables:
- `NAHES_Dataset/mediation_table_hpp_style_*_rounded.csv`
- Main summary table:
- `NAHES_Dataset/mediation_overview_all_models.csv`
- Figures:
- `NAHES_Dataset/forest_hpp_style_*.png`
- `NAHES_Dataset/effect_triplets_*.png`

