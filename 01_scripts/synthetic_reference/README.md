# Synthetic Reference Scripts

This folder contains copied upstream synthetic benchmark scripts kept for algorithm traceability.

These files are reference material for the synthetic validation story behind RetiSEM and RetiSEM-GAM. They are not the active real-data release pipeline.

## Files

- `synthetic_generator_v2_missing.py`
  - synthetic data generator with missingness support
- `generate_synthetic_dataset.py`
  - synthetic dataset assembly utility used in the upstream benchmark layer
- `run_missing_benchmark_sem_model.py`
  - broader synthetic benchmark runner containing older causal-discovery baseline comparisons
- `run_selected_methods.py`
  - convenience launcher for selected synthetic benchmark methods
- `run_our_sem_standalone.py`
  - upstream standalone RetiSEM implementation used in synthetic benchmarking
- `anti_leak.py`
  - helper utilities for synthetic benchmark leakage checks and safe split logic

## Interpretation

Use this folder when writing or explaining:

- how the synthetic datasets were generated
- how the earlier benchmark baselines were structured
- how the original standalone RetiSEM synthetic workflow was organized
