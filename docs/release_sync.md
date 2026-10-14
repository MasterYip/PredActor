# Public release synchronization

The public repository is assembled from two ownership domains. Exported
runtime files come from pinned component commits; public packaging,
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

The additive motion encoder profile maps a separately pinned MoDyeEnc commit:

```text
MoDyeEnc/finetune.py                         -> PredActor/motion_encoder/finetune.py
MoDyeEnc/prepare_data.py                     -> PredActor/motion_encoder/prepare_data.py
MoDyeEnc/src/ (explicit allowlist)           -> PredActor/motion_encoder/src/
MoDyeEnc/LICENSE                            -> PredActor/motion_encoder/LICENSE
dist/motion_encoder_overlay/docs/           -> docs/
```

Its rules live in `PDPlanner/dist/policy.motion_encoder.json` and
`.distignore.motion_encoder-source`. Both profiles export this synchronization
guide from the same `dist/collection_overlay/docs/release_sync.md` source.

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
4. Copy only the files enumerated in the generated distribution manifest.
   Payload `docs/` files go to root `docs/`; all other payload files go under
   public `PredActor/`. Verify their SHA-256 values after copying.
5. Review public-owned files separately. Do not replace the README, HF
   synchronization scripts, artifact layout, or `docs/assets/` from an export.

For encoder changes, run the additive profile separately:

```bash
python tools/dist_export.py --source . --ref <pdplanner-commit> \
  --profile motion_encoder --project-source <modyeenc-checkout> \
  --project-ref <modyeenc-commit> --output <new-payload-directory> \
  --evidence-dir <new-evidence-directory>
```

Collection exports do not own `PredActor/motion_encoder/` or
`docs/motion_encoder.md`; preserve those paths when refreshing collection.
Encoder exports do not own evaluation, collection, training, or root packaging.
Do not use whole-tree `rsync --delete` or the whole-repository `dist_sync.py`
on an additive encoder payload. The latter rejects this profile. Removal of a
previously exported file needs a separately reviewed list of obsolete owned
paths; absence from one profile is not evidence that another profile's file
is obsolete.

The public training command uses the exported
`PredActor/diffusion_policy/config_files/g1prdp_cond_diffuse.yaml`, matching the
released G1 architecture and 50-epoch recipe while resolving the dataset path through
`Artifacts/dataset/g1_152fk`.
