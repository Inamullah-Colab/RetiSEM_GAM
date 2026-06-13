# Dataset Source Reference

This file gives one compact reference table for the main external data families used in the release.

Use it for:

- quick dataset identification
- upstream source links
- reviewer reference lookup

For full workflow interpretation, use the linked detailed notes rather than repeating the full story here.

## Dataset Reference Table

| Local file / family | Role in repo | Upstream dataset / source | Reference page | Detailed note |
| --- | --- | --- | --- | --- |
| `00_inputs/raw_main/nhanes_core_for_merge.csv` | main systemic phenotype table used for exposures, outcomes, covariates, and survey weights | NHANES 2005-2006 assembled from multiple CDC domain tables | NHANES cycle page: <https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2005> | `04_docs/DATA_PROVENANCE_MAP.md` |
| `00_inputs/source_provenance/legacy_nhanes_xpt/DEMO_D.xpt` | demographics, education, poverty ratio, weights | NHANES 2005-2006 Demographics | <https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/DEMO_D.htm> | `00_inputs/source_provenance/README.md` |
| `00_inputs/source_provenance/legacy_nhanes_xpt/BPX_D.xpt` | blood pressure outcomes | NHANES 2005-2006 Blood Pressure | <https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/BPX_D.htm> | `00_inputs/source_provenance/README.md` |
| `00_inputs/source_provenance/legacy_nhanes_xpt/TRIGLY_D.xpt` | triglycerides including `LBXTR` | NHANES 2005-2006 Triglycerides | <https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/TRIGLY_D.htm> | `00_inputs/source_provenance/README.md` |
| `00_inputs/source_provenance/legacy_nhanes_xpt/BIOPRO_D.xpt` | apolipoprotein B, insulin, creatinine and related chemistry variables | NHANES 2005-2006 Biochemistry Profile | <https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/BIOPRO_D.htm> | `00_inputs/source_provenance/README.md` |
| `00_inputs/source_provenance/legacy_nhanes_xpt/ALB_CR_D.xpt` | urine albumin and urine creatinine | NHANES 2005-2006 Albumin / Creatinine Ratio | <https://wwwn.cdc.gov/Nchs/Nhanes/2005-2006/ALB_CR_D.htm> | `00_inputs/source_provenance/README.md` |
| `00_inputs/raw_main/macular_bc_prepared_with_seq.csv` | prepared retinal feature table used as mediator source | APTOS 2019 Blindness Detection images processed upstream with AutoMorph | APTOS competition page: <https://www.kaggle.com/competitions/aptos2019-blindness-detection> | `04_docs/RETINAL_SOURCE_PROVENANCE.md` |
| `00_inputs/raw_main/proxy_genetics_for_merge.csv` | proxy-genetic adjustment table used as `G` covariates | derived from NHANES `RIDRETH1` using heuristic mapping to 1000 Genomes reference superpopulations | IGSR / 1000 Genomes: <https://www.internationalgenome.org> | `04_docs/GENETIC_PROXY_METHOD.md` |

## Notes

- The NHANES clinical workflow in this release is based on assembled CSV inputs, while the original raw-domain provenance is preserved under `00_inputs/source_provenance/legacy_nhanes_xpt/`.
- The retinal workflow in this release ships the prepared feature table actually used in the analysis. The broader image-source and feature-extraction narrative should be read together with the paper.
- The proxy-genetic table is an adjustment layer only. It is not participant-level genotype data.
