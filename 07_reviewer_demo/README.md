# Reviewer Demo

This folder gives reviewers and editors one direct path to test the repository without having to reconstruct the intended branch structure.

Important scope:

- this folder covers execution and result checking for the released analysis
- it does not replace the broader provenance and audit documents for data generation

For the full audit trail, use:

- `REVIEWER_AUDIT_TRAIL.md`

## Which dataset to use

Use these in order:

1. `03_outputs/sensitivity_cluster_representative.csv`
   - this is the primary paper branch
   - it is already role-locked and model-ready
   - it is the best dataset for actual reproduction of the shipped results

2. `03_outputs/sensitivity_exposure_outcome_cluster_pruned.csv`
   - this is the stricter secondary sensitivity branch
   - use this only after the primary branch has been checked

3. `00_inputs/sample_small/sensitivity_cluster_representative_sample50.csv`
   - this is only for a fast smoke test
   - it demonstrates the workflow mechanics, not the manuscript-scale evidence

## Recommended reviewer pipeline

### Option A: 2-5 minute smoke test

Run:

```bash
python 07_reviewer_demo/run_reviewer_demo.py --mode quick
```

What it does:

- uses the shipped 50-row primary-branch sample
- runs one concrete pathway set: `LBXTR -> retinal mediators -> LBXGLU`
- fits both `linear` and `RetiSEM_GAM`
- writes outputs to `07_reviewer_demo/generated/quick/`

Expected example outputs are bundled in:

- `07_reviewer_demo/expected_outputs/quick/summary_compare.csv`
- `07_reviewer_demo/expected_outputs/quick/linear/mediation_table_linear_LBXTR_LBXGLU.csv`
- `07_reviewer_demo/expected_outputs/quick/RetiSEM_GAM/mediation_table_RetiSEM_GAM_LBXTR_LBXGLU.csv`

This is the fastest realistic check that the code path is runnable on GitHub-distributed data.

It is not a substitute for the full provenance review.

### Option B: actual primary-branch reproduction

Run:

```bash
python 07_reviewer_demo/run_reviewer_demo.py --mode primary
```

What it does:

- uses `03_outputs/sensitivity_cluster_representative.csv`
- reuses the exact shipped configuration from `05_results/sensitivity_cluster_representative_gcovars_clean/run_config.json`
- reproduces the main release comparison between `linear` and `RetiSEM_GAM`

Primary shipped result files to compare against:

- `05_results/sensitivity_cluster_representative_gcovars_clean/summary_compare.csv`
- `05_results/sensitivity_cluster_representative_gcovars_clean/linear/compact_effect_summary.csv`
- `05_results/sensitivity_cluster_representative_gcovars_clean/RetiSEM_GAM/compact_effect_summary.csv`

Bundled actual summary snapshot:

- `07_reviewer_demo/expected_outputs/primary_branch_summary_compare.csv`

### Option C: stricter sensitivity reproduction

Run:

```bash
python 07_reviewer_demo/run_reviewer_demo.py --mode sensitivity
```

What it does:

- uses `03_outputs/sensitivity_exposure_outcome_cluster_pruned.csv`
- reuses the shipped configuration from `05_results/sensitivity_exposure_outcome_cluster_pruned/run_config.json`
- reproduces the narrower sensitivity branch

Bundled actual summary snapshot:

- `07_reviewer_demo/expected_outputs/sensitivity_branch_summary_compare.csv`

## Why the primary branch is the default reviewer target

The primary reviewer target should be `sensitivity_cluster_representative` because it is the current paper-facing branch and already fixes:

- the exposure set
- the retinal mediator set
- the outcome set
- the covariate blocks
- the weight column

That makes it more realistic for peer review than asking a reviewer to rerun the raw merge or branch-construction steps first.

## If the reviewer wants the full traceability path

Read these in order:

1. `REVIEWER_AUDIT_TRAIL.md`
2. `04_docs/DATA_PROVENANCE_MAP.md`
3. `00_inputs/source_provenance/README.md`
4. `04_docs/GENETIC_PROXY_METHOD.md`
5. `01_scripts/real_data/README.md`
6. `02_model_reference/README.md`

## Interpreting the bundled actual results

The shipped main branch summary shows:

- `linear`: 273 pathways, 10 significant NIE pathways
- `RetiSEM_GAM`: 273 pathways, 10 significant NIE pathways

See:

- `07_reviewer_demo/expected_outputs/primary_branch_summary_compare.csv`

The shipped stricter sensitivity summary shows:

- `linear`: 154 pathways, 8 significant NIE pathways
- `RetiSEM_GAM`: 154 pathways, 4 significant NIE pathways

See:

- `07_reviewer_demo/expected_outputs/sensitivity_branch_summary_compare.csv`
