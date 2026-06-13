# Retinal Source Provenance

This note documents the provenance of the retinal mediator source used in the released RetiSEM-GAM workflow.

## Source used in the release

The retinal feature table used by the active release is:

- `00_inputs/raw_main/macular_bc_prepared_with_seq.csv`

This is the prepared retinal mediator source consumed by:

- `01_scripts/real_data/01_build_global_only_branches.py`
- `01_scripts/real_data/04_build_exposure_outcome_cluster_pruned_branch.py`

## Upstream retinal source

The retinal features were extracted from the APTOS diabetic retinopathy blindness dataset using the AutoMorph package.

This release does not rerun that raw image feature-extraction stage. It ships the prepared feature table produced upstream and used in the active merged workflow.

For the broader retinal image-source and feature-extraction narrative, read this note together with the paper or manuscript methods section.

So the correct interpretation is:

- raw retinal images -> AutoMorph feature extraction -> prepared retinal feature table -> NHANES matching by `SEQN` -> final branch construction

## What kind of retinal features were retained

The prepared table contains global retinal features, including:

- disc/cup geometry
- fractal dimension
- vessel density
- average width
- distance tortuosity
- squared-curvature tortuosity
- tortuosity density
- artery-specific and vein-specific versions
- zone B and zone C variants

The active paper-facing release later emphasizes the global feature family and then applies additional pruning and clustering downstream.

## How retinal records were linked to NHANES participants

The release contains the historical merge script:

- `00_inputs/source_provenance/historical_scripts/merge_cvd_with_macular_full.py`

That script shows the matching logic:

1. read the retinal feature table
2. read a `Name` to `SEQN` map
3. attach `SEQN` to retinal rows by merging on `Name`
4. normalize and deduplicate `SEQN`
5. merge retinal rows with NHANES rows on `SEQN`

The key code path is:

- `mac.merge(mseq[['Name', 'SEQN']], on='Name', how='left')`
- followed by the final NHANES merge on `SEQN`

This is the audit trail for how retinal records entered the participant-level analysis table.

## Historical merge products referenced by the old workflow

The historical workflow reports identify the combined matched retinal table as:

- `NHANES_cvd_extended_with_macular_full_matched.csv`

This is also the input referenced by:

- `00_inputs/source_provenance/historical_scripts/build_1000g_reference_proxy_features.py`
- `00_inputs/source_provenance/historical_scripts/build_model_ready_conservative_corelocked.py`

That places the retinal merge before the later proxy-adjustment and model-ready construction steps.

## How the release branch prunes the retinal block

The current paper-facing branch does not use all retinal columns directly.

The active pruning logic is in:

- `01_scripts/real_data/01_build_global_only_branches.py`

It applies:

1. a high-correlation pruning stage over global retinal candidates
2. a paper-style clustering stage over the retained global retinal features
3. selection of one representative mediator per retinal cluster, with a priority rule

The retained paper-facing mediator panel is:

- `Artery_Vessel_density`
- `Artery_Fractal_dimension`
- `Artery_Average_width`
- `Artery_Tortuosity_density`
- `Artery_Distance_tortuosity`
- `Vein_Tortuosity_density`
- `Vein_Distance_tortuosity`

Supporting release files:

- `04_docs/paper_style_global_clusters.csv`
- `04_docs/global_only_branch_manifest.json`
- `04_docs/BRANCH_SELECTION_FOR_PAPER.md`

## What a reviewer can verify from this release

A reviewer can verify:

- the exact prepared retinal feature table used in the release
- that retinal rows carry `SEQN`
- that the active real-data pipeline merges on `SEQN`
- that the later branch construction prunes and clusters retinal features explicitly
- that the final mediator panel used in the paper branch is consistent with the shipped outputs

## GitHub boundary

This release is a clean final analysis package, not a full raw-image rebuild package.

It contains:

- the prepared retinal feature table actually used in the analysis
- the historical script showing `Name -> SEQN` attachment and `SEQN` merge logic
- the current pruning/clustering logic used to derive the paper-facing mediator panel

It does not rerun:

- raw APTOS image acquisition
- AutoMorph execution on images
- earlier exploratory retinal feature-engineering variants outside the retained release workflow

The intended boundary is:

- the repository provides the prepared retinal analysis table used in the final branch
- the repository documents the participant matching and downstream pruning logic
- the paper covers the broader image-source and feature-extraction narrative
