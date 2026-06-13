# Data Provenance Map

This note explains how the new standalone release package connects the active BC workflow to the older `NAHES_Dataset` workspace.

## 1. Current Active Workflow

The primary real-data branch in this release is:

- `sensitivity_cluster_representative_gcovars_clean`

This primary branch compares:

- `linear`
- `RetiSEM_GAM`

using:

- full retained NHANES exposure block
- full retained NHANES outcome block
- cluster-representative global retinal mediators
- demographic covariates `Z`
- proxy-genetic covariates `G`

The stricter retained sensitivity branch is:

- `sensitivity_exposure_outcome_cluster_pruned`

This branch combines pruned exposures, pruned outcomes, and cluster-representative retinal mediators.

## 2. Main Input Families

The active workflow is built from three source families:

1. NHANES phenotype/clinical variables
2. Macular BC retinal biomarkers
3. Proxy-genetic reference covariates

## 3. Where They Sit in This Release

### NHANES phenotype / clinical

- final merged workflow inputs:
  - `00_inputs/raw_main/nhanes_core_for_merge.csv`
- raw-domain provenance copies:
  - `00_inputs/source_provenance/legacy_nhanes_xpt/`

### Macular BC retinal biomarkers

- active retinal source:
  - `00_inputs/raw_main/macular_bc_prepared_with_seq.csv`

### Proxy-genetic reference covariates

- active proxy source:
  - `00_inputs/raw_main/proxy_genetics_for_merge.csv`
- method note:
  - `04_docs/GENETIC_PROXY_METHOD.md`
- historical builder:
  - `00_inputs/source_provenance/historical_scripts/build_1000g_reference_proxy_features.py`

## 4. Why the Older `NAHES_Dataset` Still Matters

The older folder remains important for:

- original NHANES raw table collection
- early merge logic
- variable-history tracing
- older reports that explain how domains were assembled

But it is not the final active BC branch by itself.

The final active BC branch is represented in this release package and uses the newer global-only retinal analysis logic produced over the last few days.

## 5. Final Variable Lock Used in the Primary Branch

### Exposures

- `LBXTR`
- `LBDLDL`
- `LBXAPB`

### Outcomes

- `BPXSY2`
- `BPXDI2`
- `BPXSY3`
- `BPXDI3`
- `BPXSY4`
- `BPXDI4`
- `LBXGLU`
- `LBXGH`
- `LBXIN`
- `LBXCRP`
- `LBXSCR`
- `URXUMA`
- `URXUCR`

### Mediators

- `Artery_Vessel_density`
- `Artery_Fractal_dimension`
- `Artery_Average_width`
- `Artery_Tortuosity_density`
- `Artery_Distance_tortuosity`
- `Vein_Tortuosity_density`
- `Vein_Distance_tortuosity`

### Covariates

- Z covariates:
  - `RIDAGEYR`
  - `RIAGENDR`
  - `RIDRETH1`
  - `INDFMPIR`
  - `DMDEDUC3`
- G covariates:
  - `GREF_AMR`
  - `GREF_EUR`
  - `GREF_SAS`
  - `GREF_entropy`

## 6. Important Clarification

Proxy-genetic variables are used here as covariates, not as primary exposures.

That is the final corrected setup for this release package.

They are heuristic reference proxies derived from NHANES ethnicity categories and should not be interpreted as participant-level genotypes.

## 7. Important branch distinction

The primary branch is the one to use in the main paper because it applies explicit retinal clustering.

The exposure/outcome-pruned branch should not be described as the main clustered retinal analysis, because it applies stricter systemic pruning than the primary branch even though it keeps the same cluster-derived retinal representative panel.

## 8. Recommended GitHub Presentation

For GitHub, this release folder should be presented as:

- a clean, runnable final branch package
- a traceable package with raw-domain provenance
- a package that separates active workflow assets from historical exploratory material
