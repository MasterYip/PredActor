"""Unified G1 robot dataset driven by a YAML data-profile.

Public API
----------
G1Dataset          — main dataset class (replaces all G1_Dataset_* variants)
DataProfile        — dataclass parsed from a profile YAML
TermGroupConfig    — observation/condition group config (includes mask_config_train/infer)
TermMaskEntry      — per-term training mask schedule (used by TaskMaskGenerator)
BODY_NAMES         — ordered list of G1 body link names
JOINT_NAMES        — ordered list of G1 joint names
DEFAULT_EE_IDXS    — default end-effector body indices

Term computation and observation composition live in term_compose.py.
State normalization helpers live in state_normalize.py.
Emphasis matrix generation lives in state_emph.py.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import yaml

from diffusion_policy.dataset.offline_dataset import OfflineDataset, classproperty
from diffusion_policy.dataset.data_profile import (
    DataProfile,
    EmphConfig,
    TermGroupConfig,
    TermMaskEntry,
)
from diffusion_policy.dataset.state_emph import EmphMatGen  # re-exported for callers
from diffusion_policy.dataset.state_normalize import build_g1_reflect_ops, state_unnormalize
from diffusion_policy.dataset.term_compose import TermComposer  # re-exported for callers
from diffusion_policy.trainer.normalizer import LinearNormalizer, SingleFieldLinearNormalizer
from diffusion_policy.trainer.normalizer_cache import (
    try_load_normalizer_cache as _try_load_normalizer_cache,
    save_normalizer_cache as _save_normalizer_cache,
)
from diffusion_policy.utils.pytorch_util import dict_apply
from diffusion_policy.utils.replay_buffer import ReplayBuffer
from diffusion_policy.utils.sampler import SequenceSampler, get_val_mask
from diffusion_policy.utils.sys_monitor import check_ram_usage

# ---------------------------------------------------------------------------
# G1 skeleton constants (shared across all profiles)
# ---------------------------------------------------------------------------

BODY_NAMES = [
    "pelvis", "left_hip_pitch_link", "right_hip_pitch_link", "waist_yaw_link",
    "left_hip_roll_link", "right_hip_roll_link", "waist_roll_link", "left_hip_yaw_link",
    "right_hip_yaw_link", "torso_link", "left_knee_link", "right_knee_link",
    "left_shoulder_pitch_link", "right_shoulder_pitch_link", "left_ankle_pitch_link",
    "right_ankle_pitch_link", "left_shoulder_roll_link", "right_shoulder_roll_link",
    "left_ankle_roll_link", "right_ankle_roll_link", "left_shoulder_yaw_link",
    "right_shoulder_yaw_link", "left_elbow_link", "right_elbow_link",
    "left_wrist_roll_link", "right_wrist_roll_link", "left_wrist_pitch_link",
    "right_wrist_pitch_link", "left_wrist_yaw_link", "right_wrist_yaw_link",
]

JOINT_NAMES = [
    "left_hip_pitch_joint", "right_hip_pitch_joint", "waist_yaw_joint",
    "left_hip_roll_joint", "right_hip_roll_joint", "waist_roll_joint",
    "left_hip_yaw_joint", "right_hip_yaw_joint", "waist_pitch_joint",
    "left_knee_joint", "right_knee_joint", "left_shoulder_pitch_joint",
    "right_shoulder_pitch_joint", "left_ankle_pitch_joint", "right_ankle_pitch_joint",
    "left_shoulder_roll_joint", "right_shoulder_roll_joint", "left_ankle_roll_joint",
    "right_ankle_roll_joint", "left_shoulder_yaw_joint", "right_shoulder_yaw_joint",
    "left_elbow_joint", "right_elbow_joint", "left_wrist_roll_joint",
    "right_wrist_roll_joint", "left_wrist_pitch_joint", "right_wrist_pitch_joint",
    "left_wrist_yaw_joint", "right_wrist_yaw_joint",
]

# Default end-effector body indices (wrist_roll links: indices 17 and 18)
DEFAULT_EE_IDXS = np.array([17, 18])


@torch.no_grad()
def _update_running_feature_stats(
    running_stats, key, value, dtype=torch.float32
):
    """Merge one composed tensor into per-feature Welford statistics."""
    value = value.detach()
    if dtype is not None:
        value = value.to(dtype=dtype)
    flat = value.reshape(-1, value.shape[-1]).to(torch.float64)
    count = flat.shape[0]
    chunk_var, chunk_mean = torch.var_mean(flat, dim=0, correction=0)
    chunk_m2 = chunk_var * count
    chunk_min = flat.amin(dim=0)
    chunk_max = flat.amax(dim=0)

    if key not in running_stats:
        running_stats[key] = {
            "count": count,
            "mean": chunk_mean,
            "m2": chunk_m2,
            "min": chunk_min,
            "max": chunk_max,
        }
        return

    state = running_stats[key]
    total = state["count"] + count
    delta = chunk_mean - state["mean"]
    state["mean"] += delta * (count / total)
    state["m2"] += chunk_m2 + delta.square() * (
        state["count"] * count / total
    )
    state["min"] = torch.minimum(state["min"], chunk_min)
    state["max"] = torch.maximum(state["max"], chunk_max)
    state["count"] = total


def _finalize_running_feature_stats(running_stats):
    result = {}
    for key, state in running_stats.items():
        count = state["count"]
        if count < 2:
            std = torch.full_like(state["mean"], float("nan"))
        else:
            std = torch.sqrt(state["m2"] / (count - 1))
        result[key] = {
            "min": state["min"],
            "max": state["max"],
            "mean": state["mean"],
            "std": std,
        }
    return result


# ---------------------------------------------------------------------------
# G1Dataset — main class
# ---------------------------------------------------------------------------

class G1Dataset(OfflineDataset):
    """Unified G1 dataset driven by a DataProfile YAML.

    Replaces all G1_Dataset_* variants from g1_offline_dataset.py.

    Usage
    -----
    dataset = G1Dataset(
        zarr_path="/data/motion.zarr",
        profile="/path/to/g1_rlobs.yaml",   # or dict / OmegaConf
        horizon=20,
        n_obs_steps=4,
        symm_aug=True,
    )
    """

    # Subclasses override this to auto-select a profile when none is provided.
    _default_profile_name: str = "g1_standard"

    def __init__(
        self,
        zarr_path: str,
        data_profile=None,     # str path | dict | OmegaConf DictConfig | None → use _default_profile_name
        horizon: int = 1,
        n_obs_steps: int = 4,
        n_task_steps: int = 1,
        pad_before: int = 0,
        pad_after: int = 0,
        seed: int = 42,
        val_ratio: float = 0.0,
        load_to_memory: bool = False,
        symm_aug: bool = True,
        ee_idxs: Optional[list] = None,
        use_normalizer_cache: bool = False,
        dropout_config_train_overrides=None,
        normalizer_batch_size: int = 512,
        **kwargs,
    ):
        # Load replay buffer
        self._zarr_path = Path(zarr_path)
        self._load_to_memory = load_to_memory
        if load_to_memory:
            self.replay_buffer = ReplayBuffer.copy_from_path(zarr_path)
        else:
            self.replay_buffer = ReplayBuffer.create_from_path(zarr_path, mode="r")

        val_mask = get_val_mask(
            n_episodes=self.replay_buffer.n_episodes, val_ratio=val_ratio, seed=seed
        )
        train_mask = ~val_mask

        self.sampler = SequenceSampler(
            replay_buffer=self.replay_buffer,
            sequence_length=horizon,
            pad_before=pad_before,
            pad_after=pad_after,
            episode_mask=train_mask,
        )

        self.horizon = horizon
        self.n_obs_steps = n_obs_steps
        self.n_task_steps = n_task_steps
        self.pad_before = pad_before
        self.pad_after = pad_after
        self.train_mask = train_mask
        self.symm_aug = symm_aug
        self._use_normalizer_cache = use_normalizer_cache
        self._normalizer_batch_size = int(normalizer_batch_size)

        # Resolve profile: None → look up _default_profile_name YAML
        if data_profile is None:
            _yaml_dir = (
                Path(__file__).parent.parent / "config_files" / "defaults" / "dataset"
            )
            data_profile = _yaml_dir / f"{self.__class__._default_profile_name}.yaml"
        # Load profile
        self.data_profile = DataProfile.from_yaml(data_profile)
        self.data_profile = self.data_profile.with_dropout_config_train_overrides(
            dropout_config_train_overrides
        )
        self.ee_idxs = np.array(ee_idxs) if ee_idxs is not None else DEFAULT_EE_IDXS

        # Resolve text_cond embedding dim from the replay buffer (if present)
        _text_cond_dim = 512  # default (MotionCLIP / CLIP ViT-B/32)
        if "text_cond" in self.replay_buffer.keys():
            _text_cond_dim = self.replay_buffer["text_cond"].shape[-1]

        # Build TermComposer and reflection ops
        self.term_composer = TermComposer(self.data_profile, n_obs_steps, self.ee_idxs, text_cond_dim=_text_cond_dim, n_task_steps=n_task_steps)
        self.obs_reflect_op, self.action_reflect_op = build_g1_reflect_ops(
            self.data_profile.observation.terms, self.ee_idxs
        )
        # Reflection op for task_condition terms.  When the cond includes mixed
        # rlobs + text_cond, this is a full-size block-diagonal op (identity for
        # text_cond).  For legacy profiles with no cond terms this stays None.
        self.cond_reflect_op = None
        _cond_terms = self.data_profile.task_condition.terms
        if _cond_terms:
            cond_rop, _ = build_g1_reflect_ops(
                _cond_terms, self.ee_idxs, text_cond_dim=_text_cond_dim
            )
            self.cond_reflect_op = cond_rop

    # ------------------------------------------------------------------
    # OfflineDataset interface
    # ------------------------------------------------------------------

    def get_validation_dataset(self) -> "G1Dataset":
        val_set = copy.copy(self)
        val_set.sampler = SequenceSampler(
            replay_buffer=self.replay_buffer,
            sequence_length=self.horizon,
            pad_before=self.pad_before,
            pad_after=self.pad_after,
            episode_mask=~self.train_mask,
        )
        val_set.train_mask = ~self.train_mask
        return val_set

    @staticmethod
    def worker_init_fn(worker_id: int) -> None:
        """Rebuild replay-buffer state inside each DataLoader worker.

        The replay buffer and SequenceSampler are process-local runtime objects.
        Reusing the inherited instances from the parent process has led to
        corrupted worker state under multiprocessing. Reconstructing both from
        the dataset's persisted configuration gives each worker a clean object
        graph with fresh zarr handles.
        """
        import torch.utils.data

        worker_info = torch.utils.data.get_worker_info()
        if worker_info is None:
            return

        dataset = worker_info.dataset
        if not hasattr(dataset, "_zarr_path"):
            return

        if getattr(dataset, "_load_to_memory", False):
            replay_buffer = ReplayBuffer.copy_from_path(str(dataset._zarr_path))
        else:
            replay_buffer = ReplayBuffer.create_from_path(str(dataset._zarr_path), mode="r")

        old_sampler = getattr(dataset, "sampler", None)
        sampler_keys = getattr(old_sampler, "keys", None)
        sampler_key_first_k = dict(getattr(old_sampler, "key_first_k", {}))

        dataset.replay_buffer = replay_buffer
        dataset.sampler = SequenceSampler(
            replay_buffer=replay_buffer,
            sequence_length=dataset.horizon,
            pad_before=dataset.pad_before,
            pad_after=dataset.pad_after,
            keys=sampler_keys,
            key_first_k=sampler_key_first_k,
            episode_mask=dataset.train_mask,
        )

    def __len__(self) -> int:
        return len(self.sampler)

    def __getitem__(self, idx: int):
        # Zarr DirectoryStore + multiprocessing can intermittently fail with
        # an IndexError when a worker's cached zarr handle becomes invalid.
        # Retry with a different random index rather than crashing training.
        max_retries = 10
        for attempt in range(max_retries):
            try:
                sample = self.sampler.sample_sequence(idx)
                data = self._sample_to_data(sample)
                return dict_apply(data, torch.from_numpy)
            except (IndexError, KeyError, TypeError) as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"G1Dataset.__getitem__ failed {max_retries} times "
                        f"(last error: {e!r}). "
                        "Consider setting load_to_memory: true in dataset config."
                    ) from e
                idx = np.random.randint(0, len(self))

    def _sample_to_data(self, sample: dict) -> dict:
        """Extract raw tensors from zarr sample."""
        if "act" not in sample:
            raise KeyError("dataset sample is missing required action field 'act'")
        data = {key: value for key, value in sample.items() if key != "act"}
        data["action"] = sample["act"]
        return data

    def collate_fn(self, batch: list, normalize: bool = False) -> dict:
        """Stack batch items and compose observations via TermComposer."""
        # Stack raw tensors
        raw = {}
        sample_keys = batch[0].keys()
        for key in sample_keys:
            if key != "action":
                raw[key] = torch.stack([item[key] for item in batch])

        action = torch.stack([item["action"] for item in batch])

        # Compose observation
        obs = self.term_composer.compose_obs(raw)

        # Symmetry augmentation
        if self.symm_aug:
            obs, action = self._symmetric_augment(obs, action)

        result = {"obs": obs, "action": action}
        if "horizon_valid" in raw:
            valid_mask = raw["horizon_valid"].bool()
            if self.symm_aug:
                valid_mask = torch.cat([valid_mask, valid_mask], dim=0)
            result["valid_mask"] = valid_mask

        # Task condition: motion_latent / text_cond used as cond signal
        cond_terms = self.data_profile.task_condition.terms
        if cond_terms:
            cond = self.term_composer.compose_cond(raw)
            if self.symm_aug:
                # FIXME: The left right are not distinguished in the text_cond embedding
                cond_r = self.cond_reflect_op.to(cond.device, cond.dtype)
                cond = torch.cat([cond, cond @ cond_r.T], dim=0)
            result["cond"] = cond
        elif "motion_latent" in raw:
            # Legacy: include present-frame latent as cond even if not in profile
            print("Warning: no cond terms specified, falling back to using present-frame motion_latent as cond.")
            present = raw["motion_latent"][:, self.n_obs_steps - 1:self.n_obs_steps, :].clone()
            if self.symm_aug:
                present = torch.cat([present, present], dim=0)
            result["cond"] = present

        return result

    def _symmetric_augment(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
    ):
        act_r = self.action_reflect_op.to(action.device, action.dtype)
        if obs.shape[-1] == 0:
            obs_aug = torch.cat([obs, obs], dim=0)
        else:
            obs_r = self.obs_reflect_op.to(obs.device, obs.dtype)
            obs_aug = torch.cat([obs, obs @ obs_r.T], dim=0)
        return (
            obs_aug,
            torch.cat([action, action @ act_r.T], dim=0),
        )

    # ------------------------------------------------------------------
    # Normalizer
    # ------------------------------------------------------------------

    def get_normalizer(
        self,
        mode: str = "limits",
        data_sample_rate: float = 0.05,
        normalize_cond: bool = True,
        normalizer_batch_size: Optional[int] = None,
        sampling_seed: Optional[int] = None,
        sampling_audit: Optional[dict] = None,
        **kwargs,
    ) -> LinearNormalizer:
        """Fit a LinearNormalizer on a random sample of the dataset.

        Sampled windows are composed and reduced in bounded batches by default.
        Set ``normalizer_batch_size=0`` to use the legacy all-at-once path.

        If a ``normalizer_stats.yaml`` file exists in the same directory as the
        zarr dataset, load the pre-computed scale/offset from it instead of
        re-fitting (which can be slow for large datasets).  The file is saved
        automatically after the first fit so subsequent runs are instant.
        """
        cache_path = self._zarr_path.parent / "normalizer_stats.yaml"

        normalizer = _try_load_normalizer_cache(cache_path) if self._use_normalizer_cache else None
        if normalizer is not None:
            return normalizer

        where_non_padded = np.where(
            np.logical_and(
                self.sampler.indices[:, 3] == self.horizon,
                self.sampler.indices[:, 2] == 0,
            )
        )
        non_padded_indices = self.sampler.indices[where_non_padded]
        buffer_start_idx = non_padded_indices[:, 0]

        sample_size = max(1, int(len(buffer_start_idx) * data_sample_rate))
        if sampling_seed is None:
            selected_positions = np.random.choice(
                len(buffer_start_idx), sample_size, replace=False
            )
        else:
            selected_positions = np.random.RandomState(
                int(sampling_seed)
            ).choice(len(buffer_start_idx), sample_size, replace=False)
        buffer_start_idx = buffer_start_idx[selected_positions]
        indices = buffer_start_idx[:, None] + np.arange(self.horizon)
        if sampling_audit is not None:
            sampling_audit.update({
                "sampling_seed": (
                    None if sampling_seed is None else int(sampling_seed)
                ),
                "data_sample_rate": float(data_sample_rate),
                "eligible_window_count": int(len(non_padded_indices)),
                "sampled_window_count": int(sample_size),
                "sampled_buffer_start_indices_sha256": hashlib.sha256(
                    np.asarray(buffer_start_idx, dtype=np.int64).tobytes()
                ).hexdigest(),
                "sampled_sequence_indices_sha256": hashlib.sha256(
                    np.asarray(indices, dtype=np.int64).tobytes()
                ).hexdigest(),
            })

        # Read only the sampled rows when the aggregated replay supports it.
        # CombinedReplayBuffer.__getitem__ concatenates complete columns and can
        # exceed host memory once horizon-teacher shards accumulate.
        rb = self.replay_buffer
        indexed_keys = [
            key for key in (
                "root_pos", "root_rot", "body_pos", "body_rot",
                "body_lin_vel", "body_ang_vel", "joint_pos", "joint_vel",
                "act", "projected_gravity", "base_lin_vel", "base_ang_vel",
                "last_actions", "motion_latent", "text_cond", "horizon_valid",
                "motion_ref_root_pos", "motion_ref_root_rot",
                "motion_ref_root_lin_vel", "motion_ref_root_ang_vel",
                "motion_ref_joint_pos", "motion_ref_joint_vel",
            ) if key in rb
        ]
        def _read_indices(selected_indices):
            if hasattr(rb, "get_steps_indices"):
                flat_indices = selected_indices.reshape(-1)
                unique_indices, inverse = np.unique(
                    flat_indices, return_inverse=True
                )
                sampled_unique = rb.get_steps_indices(
                    unique_indices, keys=indexed_keys
                )
                sampled_rb = {
                    key: np.asarray(value)[inverse].reshape(
                        selected_indices.shape + np.asarray(value).shape[1:]
                    )
                    for key, value in sampled_unique.items()
                }
                raw_rb = self._sample_to_data(sampled_rb)
                return {
                    key: torch.from_numpy(np.asarray(value))
                    for key, value in raw_rb.items()
                }

            raw_rb = self._sample_to_data(rb)

            def _read_key(arr, idxs):
                flat = idxs.flatten()
                if hasattr(arr, "chunks"):
                    flat_data = arr.oindex[flat.tolist()]
                    return torch.tensor(
                        np.array(flat_data).reshape(
                            (len(idxs), self.horizon) + arr.shape[1:]
                        )
                    )
                return torch.tensor(arr[idxs])

            return {
                key: _read_key(value, selected_indices)
                for key, value in raw_rb.items()
            }

        def _collate_indices(selected_indices):
            tensor_data = _read_indices(selected_indices)
            keys = list(tensor_data.keys())
            batch = [
                {key: tensor_data[key][i] for key in keys}
                for i in range(len(selected_indices))
            ]
            return self.collate_fn(batch, normalize=True)

        batch_size = (
            self._normalizer_batch_size
            if normalizer_batch_size is None
            else int(normalizer_batch_size)
        )
        if batch_size < 0:
            raise ValueError("normalizer_batch_size must be >= 0")
        print(
            "[NormalizerFit] "
            f"sampled_windows={len(indices)} horizon={self.horizon} "
            f"batch_size={'legacy_all' if batch_size == 0 else batch_size}",
            flush=True,
        )

        if batch_size == 0:
            collated = _collate_indices(indices)
            data_for_normalizer = {
                "obs": collated["obs"].clone(),
                "action": collated["action"].clone(),
            }
            if "cond" in collated and normalize_cond:
                data_for_normalizer["cond"] = collated["cond"].clone()

            zero_dim_keys = {
                key for key, value in data_for_normalizer.items()
                if value.shape[-1] == 0
            }
            fit_data = {
                key: value for key, value in data_for_normalizer.items()
                if key not in zero_dim_keys
            }
            normalizer = LinearNormalizer()
            normalizer.fit(
                data=fit_data, last_n_dims=1, mode=mode, **kwargs
            )
            cond_dtype = (
                collated["cond"].dtype if "cond" in collated else None
            )
        else:
            running_stats = {}
            zero_dim_keys = set()
            cond_dtype = None
            stats_dtype = kwargs.get("dtype", torch.float32)
            ordered_indices = indices[
                np.argsort(indices[:, 0], kind="stable")
            ]
            for start in range(0, len(ordered_indices), batch_size):
                collated = _collate_indices(
                    ordered_indices[start:start + batch_size]
                )
                cond_dtype = (
                    collated["cond"].dtype
                    if "cond" in collated else cond_dtype
                )
                data_for_normalizer = {
                    "obs": collated["obs"],
                    "action": collated["action"],
                }
                if "cond" in collated and normalize_cond:
                    data_for_normalizer["cond"] = collated["cond"]

                for key, value in data_for_normalizer.items():
                    if value.shape[-1] == 0:
                        zero_dim_keys.add(key)
                        continue
                    _update_running_feature_stats(
                        running_stats, key, value, dtype=stats_dtype
                    )
                completed = min(start + batch_size, len(ordered_indices))
                chunk_number = start // batch_size + 1
                if (
                    chunk_number == 1
                    or chunk_number % 10 == 0
                    or completed == len(ordered_indices)
                ):
                    print(
                        "[NormalizerFit] "
                        f"processed_windows={completed}/{len(indices)}",
                        flush=True,
                    )

            fit_stats = _finalize_running_feature_stats(running_stats)
            normalizer = LinearNormalizer()
            normalizer.fit_from_stats(fit_stats, mode=mode, **kwargs)

        # Add identity normalizers for skipped zero-dim keys.
        for key in zero_dim_keys:
            normalizer[key] = SingleFieldLinearNormalizer.create_identity(
                dtype=collated[key].dtype
            )

        if cond_dtype is not None and not normalize_cond:
            normalizer["cond"] = SingleFieldLinearNormalizer.create_identity(
                dtype=cond_dtype
            )

        check_ram_usage("RAM usage after fitting normalizer")
        if self._use_normalizer_cache:
            _save_normalizer_cache(normalizer, cache_path)
        return normalizer


    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def obs_dim(self) -> int:
        return self.term_composer.obs_dim

    @property
    def profile_name(self) -> str:
        return self.data_profile.name

    @classproperty
    def body_names(cls):
        return BODY_NAMES

    @classproperty
    def joint_names(cls):
        return JOINT_NAMES

    # ------------------------------------------------------------------
    # state_unnormalize (kept for API parity with old classes)
    # ------------------------------------------------------------------

    @staticmethod
    def state_unnormalize(state, global_root=None, return_rot=False):
        return state_unnormalize(state, global_root=global_root, return_rot=return_rot)
