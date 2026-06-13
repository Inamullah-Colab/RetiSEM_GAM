# Model Reference

This folder connects the release package to the original upstream RetiSEM-GAM development code.

## `upstream_gam_sem_code`

This subfolder contains copied reference scripts from the upstream `retisem_workspace/nonlinear_stages/gam_sem/code` development layer.

These files are included so that:

- the synthetic generator logic is visible
- the benchmark runner is visible
- the original GAM-SEM method code remains traceable
- the GitHub release can point to a concrete upstream code base rather than only prose

## Important distinction

This folder is a reference layer, not the active release run layer.

The active release run layer is:

- `01_scripts/real_data`

The upstream reference layer exists to avoid misunderstanding about how `RetiSEM_GAM` was originally structured and validated.
