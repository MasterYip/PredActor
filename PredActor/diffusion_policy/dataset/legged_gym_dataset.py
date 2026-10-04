from typing import Dict, Optional, List, Tuple
import torch
import numpy as np
import copy
import json
from pathlib import Path

from diffusion_policy.utils.pytorch_util import dict_apply
from diffusion_policy.utils.replay_buffer import ReplayBuffer
from diffusion_policy.utils.sampler import (
    SequenceSampler,
    get_val_mask,
    downsample_mask,
)
from diffusion_policy.trainer.normalizer import LinearNormalizer
from diffusion_policy.trainer.normalizer_cache import try_load_normalizer_cache, save_normalizer_cache
from diffusion_policy.dataset.offline_dataset import OfflineDataset


class LeggedGymDataset(OfflineDataset):
    """
    Dataset for legged gym environments that supports variable input/output dimensions
    from different checkpoints. Inherits from OfflineDataset for diffuse_cloc compatibility.
    """

    def __init__(
        self,
        zarr_path,
        horizon=1,
        n_past_steps=3,
        pad_before=0,
        pad_after=0,
        obs_key="obs",
        state_key="obs",
        action_key="action",
        reward_key="reward",
        checkpoint_filter=None,
        seed=42,
        val_ratio=0.0,
        max_train_episodes=None,
        symm_aug=False,
        use_normalizer_cache=False,
        **kwargs
    ):
        """
        Initialize the legged gym dataset.

        Args:
            zarr_path: Path to the zarr dataset
            horizon: Number of timesteps to include in each sample
            n_past_steps: Number of past steps to include
            pad_before: Number of timesteps to pad before the sequence
            pad_after: Number of timesteps to pad after the sequence
            obs_key: Key for observations in the dataset
            state_key: Key for state in the dataset (aliased to obs_key)
            action_key: Key for actions in the dataset
            reward_key: Key for rewards in the dataset
            checkpoint_filter: List of checkpoint paths to include, or None to include all
            seed: Random seed for validation split
            val_ratio: Ratio of data to use for validation
            max_train_episodes: Maximum number of episodes to use for training
            symm_aug: Whether to use symmetric augmentation
        """
        # Load the data with relevant keys
        keys = [obs_key, action_key]
        if reward_key:
            keys.append(reward_key)

        # Add metadata keys if they exist
        metadata_keys = ['obs_dim', 'action_dim', 'checkpoint_name']

        self.replay_buffer = ReplayBuffer.copy_from_path(zarr_path, keys=keys + metadata_keys)
        self._zarr_path = Path(zarr_path)

        # Try to load metadata if available
        metadata_path = Path(zarr_path).parent / f"{Path(zarr_path).stem}_metadata.json"
        self.metadata = None
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load metadata from {metadata_path}: {e}")

        # Filter episodes by checkpoint if specified
        filtered_idxs = list(range(self.replay_buffer.n_episodes))
        if checkpoint_filter is not None:
            filtered_idxs = []
            for i in range(self.replay_buffer.n_episodes):
                try:
                    episode = self.replay_buffer.get_episode(i)
                    checkpoint = episode['checkpoint_name'][0].decode('utf-8') if isinstance(episode['checkpoint_name'][0], bytes) else str(episode['checkpoint_name'][0])
                    if any(cf in checkpoint for cf in checkpoint_filter):
                        filtered_idxs.append(i)
                except:
                    # If no checkpoint_name, include the episode
                    filtered_idxs.append(i)

            print(f"Filtered to {len(filtered_idxs)}/{self.replay_buffer.n_episodes} episodes matching checkpoint filter")

        # Create episode mask for training/validation split
        all_mask = np.zeros(self.replay_buffer.n_episodes, dtype=bool)
        all_mask[filtered_idxs] = True

        val_mask = get_val_mask(
            n_episodes=self.replay_buffer.n_episodes,
            val_ratio=val_ratio,
            seed=seed
        )

        # Only use episodes that pass both filters for validation
        val_mask = val_mask & all_mask

        # Training episodes are those that pass the checkpoint filter but aren't in validation
        train_mask = all_mask & ~val_mask

        # Downsample training episodes if max_train_episodes is specified
        if max_train_episodes is not None:
            train_mask = downsample_mask(
                mask=train_mask, max_n=max_train_episodes, seed=seed
            )

        # Create sampler for training data
        self.sampler = SequenceSampler(
            replay_buffer=self.replay_buffer,
            sequence_length=horizon,
            pad_before=pad_before,
            pad_after=pad_after,
            episode_mask=train_mask,
        )

        # Store attributes
        self.obs_key = obs_key
        self.state_key = state_key if state_key else obs_key
        self.action_key = action_key
        self.reward_key = reward_key
        self.train_mask = train_mask
        self.val_mask = val_mask
        self.horizon = horizon
        self.pad_before = pad_before
        self.pad_after = pad_after
        self.n_past_steps = n_past_steps
        self.symm_aug = symm_aug
        self._use_normalizer_cache = use_normalizer_cache

        # Cache dimensions from first episode for quick access
        first_ep_idx = np.where(train_mask)[0][0] if np.any(train_mask) else 0
        first_ep = self.replay_buffer.get_episode(first_ep_idx)
        self.example_obs_shape = first_ep[obs_key].shape[1:]
        self.example_action_shape = first_ep[action_key].shape[1:]

        # Initialize reflection operators (empty for now, can be overridden)
        self.obs_reflect_op = None
        self.action_reflect_op = None

    def get_validation_dataset(self):
        """Create a validation dataset with the same parameters."""
        val_set = copy.copy(self)
        val_set.sampler = SequenceSampler(
            replay_buffer=self.replay_buffer,
            sequence_length=self.horizon,
            pad_before=self.pad_before,
            pad_after=self.pad_after,
            episode_mask=self.val_mask,
        )
        val_set.train_mask = self.val_mask
        return val_set

    def get_normalizer(self, mode="limits", data_sample_rate=0.1, **kwargs):
        """Get a normalizer fit to the training data.

        Loads from a normalizer_stats.yaml cache next to the zarr file if available,
        otherwise fits and saves the cache for future runs.
        """
        cache_path = self._zarr_path.parent / "normalizer_stats.yaml"
        cached = try_load_normalizer_cache(cache_path) if self._use_normalizer_cache else None
        if cached is not None:
            return cached

        data = self._sample_to_data(self.replay_buffer)

        where_non_padded = np.where(
            np.logical_and(
                self.sampler.indices[:, 3] == self.horizon,
                self.sampler.indices[:, 2] == 0,
            )
        )
        non_padded_indices = self.sampler.indices[where_non_padded]
        buffer_start_idx = non_padded_indices[:, 0]

        buffer_start_idx = buffer_start_idx[
            np.random.choice(
                len(buffer_start_idx), int(len(buffer_start_idx) * data_sample_rate), replace=False
            )
        ]

        indices = buffer_start_idx[:, None] + np.arange(self.horizon)

        keys = data.keys()
        tensor_data = {key: torch.tensor(data[key][indices]) for key in keys}
        batch = [
            {key: tensor_data[key][i] for key in keys} for i in range(len(indices))
        ]

        # Apply Collate Function
        normalized_batch = self.collate_fn(batch, normalize=True)
        data["obs"] = normalized_batch["obs"].clone()
        data["action"] = normalized_batch["action"].clone()

        normalizer = LinearNormalizer()
        normalizer.fit(data=data, last_n_dims=1, mode=mode, **kwargs)
        if self._use_normalizer_cache:
            save_normalizer_cache(normalizer, cache_path)
        return normalizer

    def get_all_actions(self) -> torch.Tensor:
        """Get all actions from the dataset."""
        return torch.from_numpy(self.replay_buffer[self.action_key])

    def __len__(self) -> int:
        """Get the number of samples in the dataset."""
        return len(self.sampler)

    def _sample_to_data(self, sample):
        """Convert a sample to a data dictionary."""
        data = {
            "obs": sample[self.state_key],  # T, D_o
            "action": sample[self.action_key],  # T, D_a
        }
        return data

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """Get a sample from the dataset."""
        sample = self.sampler.sample_sequence(idx)
        data = self._sample_to_data(sample)

        torch_data = dict_apply(data, torch.from_numpy)
        return torch_data

    def collate_fn(self, batch, normalize=False):
        """Collate function for batching."""
        obs_stack = torch.stack([item["obs"] for item in batch])
        act_stack = torch.stack([item["action"] for item in batch])

        if normalize:
            pass

        return {"obs": obs_stack, "action": act_stack}

    # Utility methods for dimension handling
    def get_episode_dimensions(self) -> List[Tuple[int, int]]:
        """
        Get the observation and action dimensions for each episode in the dataset.

        Returns:
            List of (obs_dim, action_dim) tuples for each episode
        """
        dimensions = []
        for i in range(self.replay_buffer.n_episodes):
            episode = self.replay_buffer.get_episode(i)
            if 'obs_dim' in episode and 'action_dim' in episode:
                obs_dim = episode['obs_dim'][0]
                action_dim = episode['action_dim'][0]
                dimensions.append((obs_dim, action_dim))
            else:
                # Fallback to actual shape
                obs_dim = episode[self.obs_key].shape[1]
                action_dim = episode[self.action_key].shape[1]
                dimensions.append((obs_dim, action_dim))

        return dimensions

    def get_unique_dimensions(self) -> List[Tuple[int, int]]:
        """
        Get the unique observation and action dimension pairs in the dataset.

        Returns:
            List of unique (obs_dim, action_dim) tuples
        """
        all_dims = self.get_episode_dimensions()
        return list(set(all_dims))

    @classmethod
    def get_reflection_ops(cls):
        """Get reflection operators for symmetric augmentation. Override if needed."""
        return None, None

    @staticmethod
    def state_normalize(
        root_pos_frame,
        root_rot_frame,
        body_pos,
        body_rot,
        body_lin_vel,
        nominal_frame_idx,
    ):
        """Normalize state w.r.t. local frame. Override if needed."""
        pass

    @staticmethod
    def state_unnormalize(state):
        """Unnormalize state. Override if needed."""
        pass
