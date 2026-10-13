# Public release synchronization

The public repository is assembled from two ownership domains. Exported
runtime files come from a pinned PegasusMoDye commit; public packaging,
artifacts, and presentation files stay under the `PredActor` repository.

## Exported from PegasusMoDye

The collection profile maps these source paths into the public tree:

```text
PDPlanner/diffusion_policy/                  -> PredActor/diffusion_policy/
PDPlanner/train.py                           -> PredActor/train.py
RLTracker/scripts/data_collection/           -> PredActor/collection/scripts/data_collection/
RLTracker/scripts/data_dyeing/               -> PredActor/collection/scripts/data_dyeing/
RLTracker/source/rl_tracker/                 -> PredActor/collection/source/rl_tracker/
deps/train/rsl_rl-modular-normed/            -> PredActor/collection/vendor/rsl_rl-modular-normed/
dist/collection_overlay/collection/          -> PredActor/collection/
dist/collection_overlay/docs/*.md            -> docs/*.md
dist/overlay/assets/...                      -> PredActor/assets/...
```

The exact file allowlist and text adaptations are defined by
`PDPlanner/dist/policy.collection.json`. A new PegasusMoDye branch or commit
is not public automatically: export that commit, run the distribution audit,
and sync only the mapped paths.

## Maintained by PredActor

These paths are owned by the public repository and must not be overwritten by
the collection export:

```text
README.md
LICENSE
pyproject.toml
uv.lock
docs/assets/
scripts/hf_*.py
scripts/hf_manifest.yaml
Artifacts/
.github/
```

`Artifacts/` is synchronized separately with
`MasterYip/PredActor_Artifacts` on Hugging Face. It contains the PDP051 policy,
MotionCLIP checkpoint, RLTracker teacher, and the 152 retargeted G1 motion
trajectories under `motions/g1_152fk/`.

## Updating the public tree

When PegasusMoDye changes:

1. Pin the intended PegasusMoDye and external project commits.
2. Run `PDPlanner/tools/dist_export.py --profile collection`.
3. Run `PDPlanner/tools/dist_audit.py` and keep its manifest and checksums as
   release evidence outside the public Git tree.
4. Replace the exported `PredActor/` code paths and copy the exported guides
   into the public root `docs/`.
5. Review public-owned files separately. Do not replace the README, HF
   synchronization scripts, artifact layout, or `docs/assets/` from an export.

The public training command uses the exported
`PredActor/diffusion_policy/config_files/g1prdp_cond_diffuse.yaml`, matching the
PDP051 architecture and schedule while resolving the dataset path through
`Artifacts/dataset/g1_152fk`.
