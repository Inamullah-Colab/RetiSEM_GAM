# Historical Workspace Index

This note records the major top-level subfolders that existed in the older:

- `New folder/NAHES_Dataset`

workspace.

They are not copied wholesale into this release because the final BC branch should remain lighter and easier to share on GitHub.

## Historical subfolders seen in the older workspace

- `.venv`
  - local virtual environment, not needed in the release package
- `final_task`
  - older task-specific outputs and scripts
- `from_scratch_bundle_2026-02-23`
  - historical bundle from an earlier freeze point
- `from_scratch_repro_final_graph_2026-02-24`
  - older reproducibility and plotting freeze
- `platform_from_scratch_master_2026-02-24`
  - older platform-style consolidated workflow
- `r`
  - R-related workspace material
- `workflow_freeze_2026-02-24_final`
  - older frozen workflow output bundle

## Why they were not copied fully

The current release package is meant to foreground:

- the final BC real-data branch
- the active pruned exposure/outcome analysis
- the final `linear` versus `RetiSEM_GAM` comparison
- the model and manuscript assets needed for GitHub and paper preparation

Copying all historical subfolders would:

- duplicate many archived outputs
- make the release package unnecessarily heavy
- blur the distinction between active and historical workflows

## What was copied instead

To preserve the important context without overloading the package, this release keeps:

- selected raw NHANES XPT domain files
- selected historical reports
- selected historical merge/build scripts

These are the parts of the old workspace that most directly support:

- provenance
- reproducibility explanation
- manuscript writing
- GitHub organization
