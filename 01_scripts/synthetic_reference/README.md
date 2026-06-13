# Synthetic Reference Scripts

This folder contains the release-facing synthetic benchmark scripts.

It is separate from:

- `01_scripts/real_data/`
  - active real-data release workflow
- `02_model_reference/upstream_gam_sem_code/`
  - fuller upstream method-reference snapshot

This folder is for synthetic scenario generation and synthetic method evaluation.

## Files

- `synthetic_generator_v2_missing.py`
  - main synthetic benchmark scenario generator for the release-facing synthetic workflow
  - defines the benchmark scenario families, including:
    - graph size / dimensionality
    - path-length structure
    - linear versus nonlinear behavior
    - domain-constrained DAG structure
    - missingness mechanism and rate
  - builds the synthetic causal graph and node blocks used in the benchmark design
  - generates both:
    - missing-data synthetic datasets for benchmark testing
    - complete-data synthetic datasets for reference and controlled evaluation
  - exports the full synthetic benchmark package, including:
    - generated datasets
    - missingness masks
    - node lists
    - adjacency truth
    - edge-weight truth
    - effect-truth summaries such as `TE`, `NDE`, and `NIE`
  - this is the main file to read if the question is:
    - how were the synthetic benchmark scenarios actually constructed?
- `run_missing_benchmark_sem_model.py`
  - main multi-method benchmark runner for the synthetic benchmark layer
  - loads the generated synthetic datasets and associated truth objects
  - by default runs on the missing-data synthetic datasets rather than the complete-data versions
  - applies imputation where required before model fitting
  - runs multiple structure-learning / causal-discovery methods, including:
    - `PC`
    - `LINGAM`
    - `DAGMA`
    - `NOTEARS`
    - `DECI`
    - `RetiSEM`
  - converts predicted weighted graphs into adjacency predictions using thresholding rules
  - compares predicted graphs against synthetic truth using benchmark metrics such as:
    - `SHD`
    - adjacency F1
    - orientation F1
    - precision / recall
    - runtime and diagnostics
  - this is the main file to read if the question is:
    - how were methods benchmarked on the synthetic missing-data scenarios?
- `run_our_sem_standalone.py`
  - standalone synthetic evaluator for the repository's own method family
  - runs your method without the full multi-method comparison layer
  - contains multiple internal method variants, including:
    - linear-style domain-structured SEM
    - latent-SEM branch
    - GAM-style nonlinear branch most closely aligned with `RetiSEM_GAM`
  - supports both simpler linear-style estimation and more flexible nonlinear additive modeling within the synthetic benchmark setting
  - handles:
    - missing-data loading
    - optional imputation
    - truth-based evaluation
    - graph thresholding
    - output of metrics and diagnostics
  - this is the main file to read if the question is:
    - how is our own method implemented and tested on synthetic data?
- `anti_leak.py`
  - synthetic benchmark safety helper used by the evaluation scripts
  - enforces separation between:
    - training-time access to generated data
    - evaluation-time access to ground-truth graphs and truth files
  - helps prevent accidental leakage of truth information into model fitting
  - supports the anti-leak benchmark design used by:
    - `run_missing_benchmark_sem_model.py`
    - `run_our_sem_standalone.py`
  - this is the file to read if the question is:
    - how was the synthetic benchmark protected from evaluation leakage?

## Interpretation

Use this folder when writing or explaining:

- how the synthetic benchmark scenarios were generated
- how missing-data synthetic benchmarking was run
- how the repository's own method was evaluated in synthetic experiments

## Practical reading order

1. `synthetic_generator_v2_missing.py`
   - where the synthetic scenario design actually lives
2. `run_missing_benchmark_sem_model.py`
   - where multi-method benchmark evaluation is performed
3. `run_our_sem_standalone.py`
   - where the repository's own linear and nonlinear variants are evaluated directly
4. `anti_leak.py`
   - where the evaluation safety helpers live
