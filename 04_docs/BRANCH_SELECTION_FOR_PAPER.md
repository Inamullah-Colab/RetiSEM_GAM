# Branch Selection for Paper Write-up

This note fixes the branch-selection ambiguity in the release package.

## Primary branch for the paper

The branch to use for the main paper write-up is:

- `sensitivity_cluster_representative_gcovars_clean`

This is the main paper branch because:

- retinal mediators were reduced by explicit cluster-representative logic
- the exposure block was not additionally pruned
- the outcome block was not additionally pruned
- demographic covariates were kept as `Z = 5`
- proxy-genetic covariates were kept as `G = 4`
- both `linear` and `RetiSEM_GAM` converged on the same count of NIE-significant pathways

## What this branch actually prunes

This branch prunes:

- the retinal mediator block only

It does not prune:

- exposures
- outcomes
- `Z` covariates
- `G` covariates

The retained mediator panel is:

- `Artery_Vessel_density`
- `Artery_Fractal_dimension`
- `Artery_Average_width`
- `Artery_Tortuosity_density`
- `Artery_Distance_tortuosity`
- `Vein_Tortuosity_density`
- `Vein_Distance_tortuosity`

## Why this branch is preferred

The central methodological issue in this project is retinal redundancy.

Therefore the most defensible main analysis is the one that:

- explicitly clusters retinal biomarkers
- keeps one representative retinal feature from each cluster
- avoids simultaneously shrinking the systemic exposure and outcome spaces

This makes the main analysis retina-focused rather than over-controlled on all sides at once.

## Branches no longer kept in the cleaned release

Older fixed-panel and non-clustered retinal branches are no longer part of the cleaned release package.

They were excluded because they rely on earlier retinal mediator definitions that are not part of the retained cluster-based release.

## Stricter sensitivity branch

The stricter branch is:

- `sensitivity_exposure_outcome_cluster_pruned`

This branch combines:

- pruned exposures
- pruned outcomes
- cluster-representative retinal mediators
- `Z = 5`
- `G = 4`

This is the correct branch to use if you want the stricter systemic pruning while still keeping the retinal mediator block cluster-derived.

## Why the exposure/outcome-pruned branch is secondary

That branch:

- prunes exposures
- prunes outcomes
- keeps the same cluster-derived retinal mediator panel
- applies stricter systemic pruning than the main branch

So it is appropriate as:

- a robustness analysis
- a supplementary analysis
- a check that the results do not disappear after stricter systemic pruning

But it is not the cleanest branch for the main retinal-clustering story.

## Recommended manuscript language

Use wording like:

"Our primary real-data analysis used a cluster-representative global retinal branch with preserved demographic (`Z`) and proxy-genetic (`G`) adjustment. A stricter exposure/outcome-pruned branch was evaluated as a secondary sensitivity analysis."

## Summary decision

- main Results:
  - `sensitivity_cluster_representative_gcovars_clean`
- supplementary sensitivity:
  - `sensitivity_exposure_outcome_cluster_pruned`
