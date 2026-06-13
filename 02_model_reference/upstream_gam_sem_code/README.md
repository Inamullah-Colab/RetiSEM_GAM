# Upstream GAM-SEM Code Reference

This folder contains the copied upstream GAM-SEM / RetiSEM reference code used to keep the release package synchronized with the original development logic.

It is a model-reference layer, not the active release execution layer.

## Files

- `synthetic_generator_v2_missing.py`
  - upstream synthetic generator reference
- `generate_synthetic_dataset.py`
  - upstream synthetic dataset assembly script
- `run_missing_benchmark_sem_model.py`
  - upstream benchmark runner containing broader baseline comparisons
- `run_selected_methods.py`
  - launcher for selected upstream benchmark methods
- `run_our_sem_standalone.py`
  - upstream standalone RetiSEM implementation
- `anti_leak.py`
  - upstream helper utilities used by the benchmark layer

## Relationship to the active release

Use `01_scripts/real_data/` for the runnable release workflow.

Use this folder when you need:

- formulation traceability
- upstream implementation context
- synthetic/benchmark method cross-checking during manuscript writing
