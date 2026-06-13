# Synthetic And Model Reference

This note explains how the synthetic benchmark layer and the upstream model-reference layer fit into the GitHub release.

## Purpose

The repository contains three distinct layers:

1. real-data release workflow
2. synthetic benchmark workflow
3. upstream model-reference code

These should not be confused.

This note focuses on layers 2 and 3. For the real-data release workflow, use:

- `01_scripts/real_data/`
- `run_primary_release.py`
- `REVIEWER_AUDIT_TRAIL.md`

## 1. Synthetic dataset generation

The synthetic benchmark generator is in:

- `01_scripts/synthetic_reference/generate_synthetic_dataset.py`

This script generates the synthetic benchmark families used for the method-validation layer.

It defines:

- block-structured node families
  - `G`
  - `Z_fixed`
  - `Z_noise`
  - `L_treat`
  - `L_med`
  - `R`
  - `V`
- domain-constrained DAG structure
- linear and nonlinear SEM data generation
- optional missingness injection
  - `MCAR`
  - `MAR`
  - `mixed`
- Monte Carlo ground-truth effect estimation
  - `TE`
  - `NDE`
  - `NIE`

It also generates the benchmark scenario family:

- `LowDim-L`
- `LowDim-N`
- `LowDim-P`
- `LowDim-D`
- `MidDim-S`
- `MidDim-D`
- `HigDim-D`
- `HigDim-S`
- `MidDim-P`
- `MidDim-C`

The script writes separate synthetic outputs for:

- observed benchmark data
- complete benchmark data
- missingness masks
- adjacency truth
- edge-weight truth
- estimated effect truth

That separation is intentional and supports clean benchmarking.

## 2. Synthetic benchmark runners

### Broader benchmark runner

The main multi-method synthetic benchmark runner is:

- `01_scripts/synthetic_reference/run_missing_benchmark_sem_model.py`

It supports comparison across:

- `PC`
- `LINGAM`
- `DAGMA`
- `NOTEARS`
- `DECI`
- `RetiSEM`

It uses a strict anti-leak structure:

- training phase reads only synthetic data
- evaluation phase reads truth only for metrics

This is enforced through:

- `01_scripts/synthetic_reference/anti_leak.py`

### Convenience launcher

The convenience launcher is:

- `01_scripts/synthetic_reference/run_selected_methods.py`

This is a thinner wrapper around the benchmark runner and is useful when only selected methods or scenarios need to be evaluated.

## 3. Standalone RetiSEM synthetic runner

The standalone RetiSEM synthetic runner is:

- `01_scripts/synthetic_reference/run_our_sem_standalone.py`

This script evaluates the repository's own SEM-style method on the synthetic benchmark scenarios.

It supports multiple internal variants including:

- `base`
- `truth_aligned`
- `domain_structured`
- `domain_latent`
- `domain_structured_gam`
- `gam_sem`

Important practical point:

- `domain_structured_gam` / `gam_sem` is the nonlinear additive variant most closely aligned with the released `RetiSEM_GAM` story

The script also supports:

- imputation
- thresholding of estimated weighted graphs
- truth-based graph metrics
- no-truth fallback reporting

## 4. Upstream model-reference layer

The upstream reference code is in:

- `02_model_reference/upstream_gam_sem_code/`

This layer is included so the release keeps a visible method-reference connection to the earlier development code.

It is not the active real-data release runner.

It is the reference layer for:

- upstream synthetic generator logic
- upstream benchmark organization
- upstream standalone RetiSEM / GAM-SEM formulation

Use:

- `02_model_reference/README.md`

## 5. How reviewers should use this part of the repository

### If the goal is paper-result reproduction

Use:

- `01_scripts/real_data/`
- `03_outputs/`
- `05_results/`
- `07_reviewer_demo/`

Do not start with the synthetic scripts.

### If the goal is method validation / algorithm traceability

Use:

- `01_scripts/synthetic_reference/generate_synthetic_dataset.py`
- `01_scripts/synthetic_reference/run_missing_benchmark_sem_model.py`
- `01_scripts/synthetic_reference/run_selected_methods.py`
- `01_scripts/synthetic_reference/run_our_sem_standalone.py`
- `02_model_reference/upstream_gam_sem_code/`

That is the right layer for understanding:

- how the synthetic data were generated
- how methods were benchmarked
- how the upstream method story connects to the release

## 6. GitHub interpretation

For GitHub, this repository should be read as:

- a runnable real-data release package
- a documented synthetic benchmark reference package
- a method-reference package linking the release to upstream RetiSEM / GAM-SEM code

That separation is deliberate and makes the repository easier to audit.
