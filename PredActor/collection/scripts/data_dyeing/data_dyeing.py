"""
Data Dyeing Script for G1 Motion Dataset.

Encodes collected motion data into CLIP latent space using MotionCLIP.
Loads zarr dataset from data_collection.py, processes motions in batches,
and adds motion latent vectors to the dataset.

Usage:
    python data_dyeing.py
    python data_dyeing.py --config custom_config.yaml
"""

import sys
import os
from pathlib import Path
import glob

# The exported runtime keeps the encoder loader beside this script.

import torch
import numpy as np
import zarr
import hydra
from omegaconf import DictConfig, OmegaConf
from tqdm import tqdm
import yaml
import clip
from scipy import interpolate

# Import MotionCLIP utilities
from motionclip_runtime import get_motion_clip

# Import local utilities
from motion_converter import G1MotionConverter, extract_motion_window, create_motion_batches, load_motion_npz
from diffusion_policy.utils.replay_buffer import ReplayBuffer


class MotionDataDyer:
    """
    Encodes motion data into CLIP latent space.
    
    Processes collected G1 motion data and adds motion latent vectors
    using a trained MotionCLIP model.
    """
    
    def __init__(self, cfg: DictConfig):
        """
        Initialize the data dyer.
        
        Args:
            cfg: Hydra configuration
        """
        self.cfg = cfg
        self.device = torch.device(cfg.motionclip.device)
        
        print("="*80)
        print("Motion Data Dyeing - CLIP Latent Encoding")
        print("="*80)
        
        # Load MotionCLIP model
        print(f"\n[1/4] Loading MotionCLIP model...")
        print(f"  Checkpoint: {cfg.motionclip.checkpoint_path}")
        
        if not os.path.exists(cfg.motionclip.checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {cfg.motionclip.checkpoint_path}")
        
        self.model, self.model_cfg = get_motion_clip(
            checkpoint_path=cfg.motionclip.checkpoint_path,
            device=cfg.motionclip.device
        )
        self.model.eval()
        
        print(f"  Model loaded successfully!")
        print(f"  Latent dim: {self.model_cfg.model.latent_dim}")
        print(f"  Num frames: {self.model_cfg.model.num_frames}")
        
        # Initialize motion converter
        self.converter = G1MotionConverter(
            pose_rep=cfg.encoding.pose_rep,
            translation=cfg.encoding.translation,
            glob=cfg.encoding.glob,
            device=self.device
        )
        
        # Validate window size matches model
        if cfg.encoding.window_size != self.model_cfg.model.num_frames:
            print(f"\n  WARNING: window_size ({cfg.encoding.window_size}) != "
                  f"model.num_frames ({self.model_cfg.model.num_frames})")
            print(f"  Using model.num_frames = {self.model_cfg.model.num_frames}")
            self.window_size = self.model_cfg.model.num_frames
        else:
            self.window_size = cfg.encoding.window_size
        
        # Store FPS conversion parameters
        self.origin_fps = cfg.encoding.get('origin_fps', 30)
        self.target_fps = cfg.encoding.get('target_fps', 30)
        self.interp_method = cfg.encoding.get('interp_method', 'linear')
        
        if self.origin_fps != self.target_fps:
            print(f"\n  FPS Conversion enabled: {self.origin_fps} Hz → {self.target_fps} Hz")
            print(f"  Interpolation method: {self.interp_method}")
        
        # Load vocabulary if using text-aligned encoding
        self.text_features_norm = None
        self.text_alignment_temperature = cfg.encoding.get('text_alignment_temperature', 1.0)
        if cfg.encoding.get('use_text_alignment', False):
            self._load_vocabulary()
    
    def _load_vocabulary(self):
        """Load vocabulary and encode with CLIP text encoder."""
        print(f"\n  Loading vocabulary for text alignment...")
        vocab_path = self.cfg.encoding.vocabulary_path
        
        if not os.path.exists(vocab_path):
            raise FileNotFoundError(f"Vocabulary file not found: {vocab_path}")
        
        # Load vocabulary from YAML
        with open(vocab_path, 'r') as f:
            vocab_config = yaml.safe_load(f)
        
        # Flatten vocabulary into a list
        vocabulary = []
        for category, texts in vocab_config.get('vocabulary_categories', {}).items():
            vocabulary.extend(texts)
        # Remove duplicates
        vocabulary = list(set(vocabulary))

        print(f"  Loaded {len(vocabulary)} text descriptions")
        
        # Encode vocabulary with CLIP (same as dyed_data_vis.py)
        print(f"  Encoding vocabulary with CLIP text encoder...")
        text_tokens = clip.tokenize(vocabulary).to(self.device)
        
        with torch.no_grad():
            text_features = self.model.clip_model.encode_text(text_tokens).float()
            self.text_features_norm = text_features / text_features.norm(dim=-1, keepdim=True)
        
        print(f"  Text features shape: {self.text_features_norm.shape}")
        print(f"  Text alignment enabled with temperature: {self.text_alignment_temperature}")
    
    def load_dataset(self):
        """Load input zarr dataset."""
        print(f"\n[2/4] Loading input dataset...")
        print(f"  Path: {self.cfg.input.zarr_path}")
        
        if not os.path.exists(self.cfg.input.zarr_path):
            raise FileNotFoundError(f"Dataset not found: {self.cfg.input.zarr_path}")
        
        # Load using ReplayBuffer (same as data_collection.py)
        self.buffer = ReplayBuffer.copy_from_path(self.cfg.input.zarr_path)
        
        # Get dataset info
        self.total_frames = self.buffer.n_steps
        
        print(f"  Total frames: {self.total_frames}")
        print(f"  Total episodes: {self.buffer.n_episodes}")
        print(f"  Fields: {list(self.buffer.data.keys())}")
        
        # Pre-compute episode indices for each frame
        # This maps each frame to its episode index and boundaries
        episode_ends = self.buffer.episode_ends[:]
        self.frame_to_episode = np.zeros(self.total_frames, dtype=np.int64)
        self.episode_starts = np.zeros(len(episode_ends), dtype=np.int64)
        self.episode_ends_arr = episode_ends.copy()
        
        for ep_idx in range(len(episode_ends)):
            start = 0 if ep_idx == 0 else episode_ends[ep_idx - 1]
            end = episode_ends[ep_idx]
            self.episode_starts[ep_idx] = start
            self.frame_to_episode[start:end] = ep_idx
        
        print(f"  Episode boundaries computed")
        
        # Check required fields
        required_fields = ['body_pos', 'body_rot']
        for field in required_fields:
            if field not in self.buffer.data:
                raise ValueError(f"Required field '{field}' not found in dataset")
        
        print(f"  Dataset loaded successfully!")
    
    def load_origin_motions(self):
        """
        Load original motion files (npz) for dyeing.
        
        Returns cached latents indexed by motion_idx.
        """
        print(f"\n[2/4] Loading and encoding original motions...")
        
        # Find motion files using glob pattern (same as data_collection.py)
        motion_pattern = self.cfg.input.motion_pattern
        motion_base_path = Path(self.cfg.input.get('motion_base_path', './artifacts'))
        motion_files = sorted(glob.glob(str(motion_base_path / motion_pattern / "motion.npz")))
        
        if not motion_files:
            raise FileNotFoundError(f"No motion files found: {motion_base_path / motion_pattern / 'motion.npz'}")
        
        print(f"  Found {len(motion_files)} motion files")
        print(f"  Pattern: {motion_pattern}")
        
        # Load zarr to get motion_idx field
        if not os.path.exists(self.cfg.input.zarr_path):
            raise FileNotFoundError(f"Dataset not found: {self.cfg.input.zarr_path}")
        
        self.buffer = ReplayBuffer.copy_from_path(self.cfg.input.zarr_path)
        self.total_frames = self.buffer.n_steps
        
        # Check motion_idx field exists
        if 'motion_idx' not in self.buffer.data:
            raise ValueError("Dataset does not contain 'motion_idx' field. Cannot use dyeing_from_origin_motion mode.")
        
        print(f"  Dataset: {self.total_frames} frames, {self.buffer.n_episodes} episodes")
        
        # Encode each original motion and cache latents
        latent_dim = self.model_cfg.model.latent_dim
        motion_latents_cache = {}  # motion_idx -> [T_motion, latent_dim]
        
        for motion_idx, motion_file in enumerate(tqdm(motion_files, desc="Encoding motions")):
            motion_name = Path(motion_file).parent.name
            
            # Load motion from npz
            motion_data = load_motion_npz(motion_file, device=self.device)
            motion_length = motion_data['motion_length']
            motion_fps = motion_data['fps']
            
            # Encode this motion
            motion_latents = self._encode_single_motion(motion_data)  # [T_motion, latent_dim]
            motion_latents_cache[motion_idx] = motion_latents.cpu().numpy()
            
            print(f"  [{motion_idx}] {motion_name}: {motion_length} frames @ {motion_fps} fps -> latents {motion_latents.shape}")
        
        print(f"  Cached {len(motion_latents_cache)} motion latents")
        
        return motion_latents_cache
    
    def _encode_single_motion(self, motion_data):
        """
        Encode a single motion sequence to latent vectors.
        
        Args:
            motion_data: Dictionary with motion data from load_motion_npz
        
        Returns:
            latents: [T_motion, latent_dim] tensor
        """
        motion_length = motion_data['motion_length']
        latent_dim = self.model_cfg.model.latent_dim
        latents = torch.zeros(motion_length, latent_dim, device=self.device)
        
        # Process in batches
        batch_size = self.cfg.encoding.batch_size
        
        with torch.no_grad():
            for start_idx in range(0, motion_length, batch_size):
                end_idx = min(start_idx + batch_size, motion_length)
                batch_center_indices = list(range(start_idx, end_idx))
                
                # Extract windows for each frame in batch
                batch_windows = []
                for center_idx in batch_center_indices:
                    # Extract window centered at this frame
                    window_data = self._extract_motion_window_from_data(
                        motion_data, center_idx, motion_length
                    )
                    batch_windows.append(window_data)
                
                # Stack into batch
                batch_dict = {
                    'body_pos': torch.stack([w['body_pos'] for w in batch_windows]),  # [B, T, 30, 3]
                    'body_rot': torch.stack([w['body_rot'] for w in batch_windows]),  # [B, T, 30, 4]
                }
                if 'body_lin_vel' in batch_windows[0]:
                    batch_dict['body_lin_vel'] = torch.stack([w['body_lin_vel'] for w in batch_windows])
                if 'body_ang_vel' in batch_windows[0]:
                    batch_dict['body_ang_vel'] = torch.stack([w['body_ang_vel'] for w in batch_windows])
                
                # Convert each sample in batch to MotionCLIP format
                batch_converted = []
                for i in range(len(batch_center_indices)):
                    converted = self.converter.convert(
                        batch_dict['body_pos'][i],  # [T, 30, 3]
                        batch_dict['body_rot'][i],  # [T, 30, 4]
                        batch_dict.get('body_lin_vel', [None]*len(batch_center_indices))[i] if 'body_lin_vel' in batch_dict else None,
                        batch_dict.get('body_ang_vel', [None]*len(batch_center_indices))[i] if 'body_ang_vel' in batch_dict else None,
                    )
                    batch_converted.append(converted)
                
                # Stack and encode
                batch_tensor = torch.stack(batch_converted)  # [B, bodies, features, time]
                batch_lengths = torch.tensor([self.window_size] * len(batch_center_indices), 
                                            dtype=torch.long, device=self.device)
                
                # Encode with MotionCLIP (same pattern as encode_motions)
                mask = self.model.lengths_to_mask(batch_lengths)
                dummy_labels = torch.zeros(len(batch_center_indices), dtype=torch.long, device=self.device)
                
                encoded = self.model.encoder({
                    'x': batch_tensor,
                    'y': dummy_labels,
                    'mask': mask
                })
                
                motion_latents_batch = encoded['mu']  # [B, latent_dim]
                
                # Apply text alignment if enabled
                if self.text_features_norm is not None:
                    motion_latents_batch = self._align_to_text(motion_latents_batch)
                
                # IMPORTANT: Norm Normalization
                motion_latents_batch = motion_latents_batch / motion_latents_batch.norm(dim=-1, keepdim=True)
                
                # Store batch results
                latents[start_idx:end_idx] = motion_latents_batch
        
        return latents
    
    def _extract_motion_window_from_data(self, motion_data, center_idx, motion_length):
        """Extract motion window from loaded motion data."""
        half_window = self.window_size // 2
        start_idx = center_idx - half_window
        end_idx = center_idx + half_window
        
        # Handle boundaries with padding
        if start_idx < 0:
            left_pad = -start_idx
            actual_start = 0
        else:
            left_pad = 0
            actual_start = start_idx
        
        if end_idx > motion_length:
            right_pad = end_idx - motion_length
            actual_end = motion_length
        else:
            right_pad = 0
            actual_end = end_idx
        
        # Extract window
        window_dict = {
            'body_pos': motion_data['body_pos'][actual_start:actual_end],
            'body_rot': motion_data['body_rot'][actual_start:actual_end],
        }
        
        if 'body_lin_vel' in motion_data:
            window_dict['body_lin_vel'] = motion_data['body_lin_vel'][actual_start:actual_end]
        if 'body_ang_vel' in motion_data:
            window_dict['body_ang_vel'] = motion_data['body_ang_vel'][actual_start:actual_end]
        
        # Pad if needed
        for key, value in window_dict.items():
            if left_pad > 0:
                pad_value = value[0:1].repeat(left_pad, *([1] * (value.ndim - 1)))
                value = torch.cat([pad_value, value], dim=0)
            if right_pad > 0:
                pad_value = value[-1:].repeat(right_pad, *([1] * (value.ndim - 1)))
                value = torch.cat([value, pad_value], dim=0)
            window_dict[key] = value
        
        return window_dict
    
    def attach_cached_latents(self, motion_latents_cache):
        """
        Attach cached motion latents to dataset samples based on motion_idx.
        
        Args:
            motion_latents_cache: Dict mapping motion_idx -> [T_motion, latent_dim]
        
        Returns:
            all_latents: [total_frames, latent_dim] array
        """
        print(f"\n[3/4] Attaching cached latents to dataset samples...")
        
        latent_dim = self.model_cfg.model.latent_dim
        all_latents = np.zeros((self.total_frames, latent_dim), dtype=np.float32)
        
        # Get motion_idx for each frame and episode boundaries
        episode_ends = self.buffer.episode_ends[:]
        frame_to_episode = np.zeros(self.total_frames, dtype=np.int64)
        episode_starts = np.zeros(len(episode_ends), dtype=np.int64)
        
        for ep_idx in range(len(episode_ends)):
            start = 0 if ep_idx == 0 else episode_ends[ep_idx - 1]
            end = episode_ends[ep_idx]
            episode_starts[ep_idx] = start
            frame_to_episode[start:end] = ep_idx
        
        # Process each episode
        motion_idx_data = self.buffer['motion_idx'][:]  # [total_frames, 1]
        
        # Get length mismatch policy
        mismatch_policy = self.cfg.input.get('length_mismatch_policy', 'drop_all')
        
        mismatches = []
        valid_episodes = []  # Track episodes that match
        clipped_episodes = []  # Track episodes that were clipped
        slight_clip_episodes = []  # Track episodes that were slightly clipped
        for ep_idx in tqdm(range(self.buffer.n_episodes), desc="Attaching latents"):
            ep_start = episode_starts[ep_idx]
            ep_end = episode_ends[ep_idx]
            ep_length = ep_end - ep_start
            
            # Get motion_idx for this episode (should be constant)
            motion_idx = int(motion_idx_data[ep_start])
            
            if motion_idx not in motion_latents_cache:
                print(f"  [WARNING] Episode {ep_idx} has motion_idx={motion_idx} not in cache. Skipping.")
                mismatches.append((ep_idx, motion_idx, ep_length, -1, 'not_in_cache'))
                continue
            
            # Get cached latents for this motion
            motion_latents = motion_latents_cache[motion_idx]  # [T_motion, latent_dim]
            motion_length = motion_latents.shape[0]
            
            # Check length compatibility
            if ep_length != motion_length:
                if mismatch_policy == "clip_or_drop":
                    if ep_length < motion_length:
                        # Sample shorter than motion: clip motion to match sample
                        all_latents[ep_start:ep_end] = motion_latents[:ep_length]
                        valid_episodes.append(ep_idx)
                        if ep_length == motion_length -1:
                            slight_clip_episodes.append((ep_idx, motion_idx, ep_length, motion_length))
                        else:
                            clipped_episodes.append((ep_idx, motion_idx, ep_length, motion_length))
                    else:
                        # Sample longer than motion: drop episode
                        print(f"  [WARNING] Episode {ep_idx} length {ep_length} > motion {motion_idx} length {motion_length}. Dropping.")
                        mismatches.append((ep_idx, motion_idx, ep_length, motion_length, 'too_long'))
                        continue
                        
                elif mismatch_policy == "interpolate":
                    # Use linear interpolation to align
                    indices = np.linspace(0, motion_length - 1, ep_length)
                    resampled_latents = np.zeros((ep_length, latent_dim), dtype=np.float32)
                    for feat_idx in range(latent_dim):
                        resampled_latents[:, feat_idx] = np.interp(
                            indices, np.arange(motion_length), motion_latents[:, feat_idx]
                        )
                    all_latents[ep_start:ep_end] = resampled_latents
                    valid_episodes.append(ep_idx)
                    
                else:  # drop_all (default)
                    print(f"  [WARNING] Episode {ep_idx} length {ep_length} != motion {motion_idx} length {motion_length}. Skipping.")
                    mismatches.append((ep_idx, motion_idx, ep_length, motion_length, 'mismatch'))
                    continue
            else:
                # Direct copy - perfect match
                all_latents[ep_start:ep_end] = motion_latents
                valid_episodes.append(ep_idx)
        
        # Print statistics
        if slight_clip_episodes:
            print(f"\n  [INFO] Slightly clipped {len(slight_clip_episodes)} episodes (sample == motion - 1):")

        if clipped_episodes:
            print(f"\n  [INFO] Clipped {len(clipped_episodes)} episodes (sample < motion):")
            for ep_idx, motion_idx, ep_len, motion_len in clipped_episodes[:10]:
                print(f"    Episode {ep_idx} (motion {motion_idx}): clipped {motion_len} -> {ep_len} frames")
            if len(clipped_episodes) > 10:
                print(f"    ... and {len(clipped_episodes) - 10} more")
        
        if mismatches:
            print(f"\n  [INFO] Skipping {len(mismatches)} episodes:")
            print(f"  (These episodes will be removed from the saved dataset)")
            for ep_idx, motion_idx, ep_len, motion_len, reason in mismatches[:10]:
                if reason == 'not_in_cache':
                    print(f"    Episode {ep_idx} (motion {motion_idx}): motion not in cache")
                elif reason == 'too_long':
                    print(f"    Episode {ep_idx} (motion {motion_idx}): {ep_len} frames > {motion_len} original (too long)")
                else:
                    print(f"    Episode {ep_idx} (motion {motion_idx}): {ep_len} frames vs {motion_len} original")
            if len(mismatches) > 10:
                print(f"    ... and {len(mismatches) - 10} more")
        
        print(f"\n  Policy: '{mismatch_policy}'")
        print(f"  Attached latents for {len(valid_episodes)}/{self.buffer.n_episodes} episodes")
        print(f"  - Perfect matches: {len(valid_episodes) - len(clipped_episodes) - len(slight_clip_episodes)}")
        print(f"  - Slightly clipped (sample == motion - 1): {len(slight_clip_episodes)}")
        print(f"  - Clipped (sample < motion - 1): {len(clipped_episodes)}")
        print(f"  - Removed: {len(mismatches)}")
        
        return all_latents, valid_episodes
    
    def encode_motions(self):
        """Encode all motions to CLIP latent space."""
        print(f"\n[3/4] Encoding motions to CLIP latent space...")
        print(f"  Window size: {self.window_size}")
        print(f"  Batch size: {self.cfg.encoding.batch_size}")
        print(f"  Boundary mode: {self.cfg.encoding.boundary_mode}")
        
        # Prepare output array for latents
        latent_dim = self.model_cfg.model.latent_dim
        all_latents = np.zeros((self.total_frames, latent_dim), dtype=np.float32)
        
        # Create batches
        batches = create_motion_batches(
            self.total_frames,
            self.window_size,
            self.cfg.encoding.batch_size,
            self.cfg.encoding.boundary_mode
        )
        
        print(f"  Total batches: {len(batches)}")
        
        # Process batches
        with torch.no_grad():
            pbar = tqdm(batches, desc="Encoding motions")
            
            for batch_idx, (batch_start, batch_end, center_indices) in enumerate(pbar):
                # Prepare batch data
                batch_motions = []
                batch_lengths = []
                
                for center_idx in center_indices:
                    # Extract motion window
                    window_data = self._extract_window(center_idx)
                    
                    # Convert to MotionCLIP format
                    motion_tensor = self.converter.convert(
                        body_pos=window_data['body_pos'],
                        body_rot=window_data['body_rot'],
                        body_lin_vel=window_data.get('body_lin_vel'),
                        body_ang_vel=window_data.get('body_ang_vel')
                    )
                    # Shape: [30 or 31, feat_dim, window_size]
                    
                    batch_motions.append(motion_tensor)
                    batch_lengths.append(self.window_size)
                
                # Stack batch
                batch_motions = torch.stack(batch_motions, dim=0)  # [B, bodies, feat_dim, T]
                batch_lengths = torch.tensor(batch_lengths, dtype=torch.long, device=self.device)
                
                # Encode with MotionCLIP
                mask = self.model.lengths_to_mask(batch_lengths)
                dummy_labels = torch.zeros(len(center_indices), dtype=torch.long, device=self.device)
                
                encoded = self.model.encoder({
                    'x': batch_motions,
                    'y': dummy_labels,
                    'mask': mask
                })
                
                latent_features = encoded['mu']  # [B, latent_dim]
                
                # Apply text alignment if enabled
                if self.text_features_norm is not None:
                    latent_features = self._align_to_text(latent_features)
                
                # IMPORTANT: Norm Normalization
                latent_features = latent_features / latent_features.norm(dim=-1, keepdim=True)

                # Store latents
                all_latents[batch_start:batch_end] = latent_features.cpu().numpy()
                
                # Update progress
                if self.cfg.logging.verbose and batch_idx % self.cfg.logging.log_interval == 0:
                    pbar.set_postfix({
                        'batch': f"{batch_idx+1}/{len(batches)}",
                        'frames': f"{batch_end}/{self.total_frames}"
                    })
        
        print(f"  Encoding complete!")
        print(f"  Latent shape: {all_latents.shape}")
        
        return all_latents
    
    def _resample_motion_window(self, motion_data):
        """
        Resample motion window from origin_fps to target_fps.
        
        Always produces exactly self.window_size frames at target_fps.
        
        Args:
            motion_data: Dict with 'body_pos', 'body_rot', etc. [T_orig, ...]
        
        Returns:
            resampled_data: Dict with resampled motion data [window_size, ...]
        """
        if self.origin_fps == self.target_fps:
            return motion_data  # No resampling needed
        
        # Get original number of frames
        T_orig = motion_data['body_pos'].shape[0]
        
        # Target is exactly self.window_size frames
        T_new = self.window_size
        
        # Create time arrays
        # Original: frames at origin_fps
        t_orig = np.arange(T_orig) / self.origin_fps
        
        # Target: exactly window_size frames at target_fps, centered
        # This ensures we sample {..., t-1/target_fps, t, t+1/target_fps, ...}
        duration_target = (T_new - 1) / self.target_fps
        t_new = np.linspace(0, duration_target, T_new)
        
        # Resample each field
        resampled_data = {}
        
        for key, data in motion_data.items():
            if data is None:
                resampled_data[key] = None
                continue
            
            # Handle different interpolation methods
            if self.interp_method == 'nearest':
                kind = 'nearest'
            elif self.interp_method == 'cubic':
                kind = 'cubic'
            else:  # linear
                kind = 'linear'
            
            # For multi-dimensional data, interpolate along first axis
            original_shape = data.shape
            data_flat = data.reshape(T_orig, -1)  # [T, features]
            
            # Create interpolator
            f = interpolate.interp1d(t_orig, data_flat, axis=0, kind=kind, 
                                    fill_value='extrapolate')
            
            # Resample to exactly window_size frames
            resampled_flat = f(t_new)
            
            # Reshape back
            new_shape = (T_new,) + original_shape[1:]
            resampled_data[key] = resampled_flat.reshape(new_shape)
        
        return resampled_data
    
    def _align_to_text(self, motion_latents):
        """
        Align motion latents to text embedding space using vocabulary-weighted averaging.
        
        This computes similarity between motion latents and all text embeddings,
        then creates a new embedding as a weighted average of text embeddings.
        This bridges the semantic gap between motion and text embeddings.
        
        Args:
            motion_latents: Motion latent vectors [B, latent_dim]
        
        Returns:
            text_aligned_latents: Text-aligned latent vectors [B, latent_dim]
        """
        # Normalize motion latents (same as dyed_data_vis.py)
        motion_latents_norm = motion_latents / motion_latents.norm(dim=-1, keepdim=True)
        
        # Compute similarity with all text descriptions [B, num_texts]
        # Using same formula as dyed_data_vis.py, but with temperature control
        # Lower temperature -> sharper distribution (more focused on top matches)
        # Higher temperature -> smoother distribution (more uniform weighting)
        logits = motion_latents_norm @ self.text_features_norm.t()
        similarity = (logits / self.text_alignment_temperature).softmax(dim=-1)
        
        # Compute weighted average of text embeddings
        # text_aligned = sum(similarity[i] * text_embedding[i])
        # Shape: [B, num_texts] @ [num_texts, latent_dim] = [B, latent_dim]
        text_aligned_latents = similarity @ self.text_features_norm
        
        return text_aligned_latents
    
    def _extract_window(self, center_idx):
        """Extract motion window for a specific frame."""
        # Determine which episode this frame belongs to
        episode_idx = self.frame_to_episode[center_idx]
        episode_start = self.episode_starts[episode_idx]
        episode_end = self.episode_ends_arr[episode_idx]
        
        # Create data dict from buffer
        data_dict = {
            'body_pos': self.buffer['body_pos'][:],
            'body_rot': self.buffer['body_rot'][:],
        }
        
        # Add optional fields if available
        if 'body_lin_vel' in self.buffer.data:
            data_dict['body_lin_vel'] = self.buffer['body_lin_vel'][:]
        if 'body_ang_vel' in self.buffer.data:
            data_dict['body_ang_vel'] = self.buffer['body_ang_vel'][:]
        
        # Extract window at original FPS
        # Need to adjust window size for original FPS
        if self.origin_fps != self.target_fps:
            # Calculate window size at original FPS to get target duration
            target_duration = (self.window_size - 1) / self.target_fps  # Duration in seconds
            origin_window_size = int(target_duration * self.origin_fps) + 1
        else:
            origin_window_size = self.window_size
        
        window_data = extract_motion_window(
            data_dict,
            center_idx,
            origin_window_size,
            self.cfg.encoding.boundary_mode,
            episode_start=episode_start,
            episode_end=episode_end
        )
        
        # Resample to target FPS if needed
        if self.origin_fps != self.target_fps:
            window_data = self._resample_motion_window(window_data)
        
        return window_data
    
    def save_dataset(self, latents, valid_episodes=None):
        """Save dataset with added latent vectors.
        
        Args:
            latents: Latent vectors for all frames
            valid_episodes: Optional list of valid episode indices to keep
        """
        print(f"\n[4/4] Saving dataset with latent vectors...")
        print(f"  Output path: {self.cfg.output.zarr_path}")
        
        # Filter buffer if valid_episodes is provided
        if valid_episodes is not None and len(valid_episodes) != self.buffer.n_episodes:
            print(f"  Filtering dataset to keep only {len(valid_episodes)}/{self.buffer.n_episodes} valid episodes...")
            
            # First, filter latents to match valid episodes
            # Compute which frames belong to valid episodes
            episode_ends = self.buffer.episode_ends[:]
            
            # Build mask for valid frames
            valid_frame_mask = np.zeros(self.total_frames, dtype=bool)
            for ep_idx in valid_episodes:
                ep_start = 0 if ep_idx == 0 else episode_ends[ep_idx - 1]
                ep_end = episode_ends[ep_idx]
                valid_frame_mask[ep_start:ep_end] = True
            
            # Filter latents
            latents = latents[valid_frame_mask]
            print(f"  Filtered latents: {latents.shape}")
            
            # Create filtered buffer with only valid episodes
            filtered_buffer = ReplayBuffer.create_empty_zarr()
            
            for ep_idx in tqdm(valid_episodes, desc="Copying valid episodes"):
                # Get episode slice
                episode = self.buffer.get_episode(ep_idx)
                # Add to filtered buffer
                filtered_buffer.add_episode(episode)
            
            # Replace buffer with filtered version
            self.buffer = filtered_buffer
            self.total_frames = self.buffer.n_steps
            
            print(f"  Filtered dataset: {self.total_frames} frames, {self.buffer.n_episodes} episodes")
        
        # Create output directory
        output_dir = os.path.dirname(self.cfg.output.zarr_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Add latent field to buffer's data
        latent_field = self.cfg.output.latent_field_name
        
        # Check if field exists
        if latent_field in self.buffer.data:
            if self.cfg.output.overwrite:
                print(f"  Overwriting existing '{latent_field}' field...")
                # Delete from buffer if using zarr backend
                if self.buffer.backend == 'zarr':
                    del self.buffer.data[latent_field]
            else:
                raise ValueError(f"Field '{latent_field}' already exists. Set overwrite=true to replace.")
        
        print(f"  Adding '{latent_field}' field...")
        
        # Add latent field to buffer's data dict
        if self.buffer.backend == 'numpy':
            self.buffer.data[latent_field] = latents
        else:
            # For zarr backend, we need to add it to the data group
            # Set compression
            if self.cfg.output.compressor == 'blosc':
                from numcodecs import Blosc
                compressor = Blosc(cname='zstd', clevel=5, shuffle=Blosc.BITSHUFFLE)
            elif self.cfg.output.compressor == 'default':
                compressor = ReplayBuffer.resolve_compressor('default')
            else:
                compressor = None
            
            self.buffer.data.array(
                latent_field,
                latents,
                chunks=(1000, latents.shape[1]),
                dtype=np.float32,
                compressor=compressor
            )
        
        # Save buffer to output path
        print(f"  Saving buffer to disk...")
        
        # Set compression for saving
        compressor_dict = {latent_field: self.cfg.output.compressor}
        if self.cfg.output.compressor == 'blosc':
            compressor_dict = {latent_field: 'disk'}  # Use 'disk' for high compression
        
        self.buffer.save_to_path(
            self.cfg.output.zarr_path,
            compressors=compressor_dict,
            if_exists='replace',
            verbose=True
        )
        
        print(f"  Dataset saved successfully!")
        if os.path.exists(self.cfg.output.zarr_path):
            # Calculate directory size for zarr
            total_size = sum(f.stat().st_size for f in Path(self.cfg.output.zarr_path).rglob('*') if f.is_file())
            print(f"  Total size: {total_size / 1024**2:.2f} MB")
        
        # Print summary
        print("\n" + "="*80)
        print("Data Dyeing Complete!")
        print("="*80)
        print(f"Input dataset: {self.cfg.input.zarr_path}")
        print(f"Output dataset: {self.cfg.output.zarr_path}")
        print(f"Total frames: {self.total_frames}")
        print(f"Total episodes: {self.buffer.n_episodes}")
        print(f"Latent field: '{latent_field}' with shape {latents.shape}")
        print(f"Latent dim: {latents.shape[1]}")
        print("="*80)


@hydra.main(version_base=None, config_path=".", config_name="data_dyeing")
def main(cfg: DictConfig):
    """Main entry point."""
    
    # Print configuration
    print("\nConfiguration:")
    print(OmegaConf.to_yaml(cfg))
    
    # Initialize dyer
    dyer = MotionDataDyer(cfg)
    
    # Check if dyeing from origin motions
    if cfg.input.get('dyeing_from_origin_motion', False):
        print("\n" + "="*80)
        print("Using ORIGIN MOTION DYEING mode")
        print("="*80)
        print(f"Loading original motion files from: {cfg.input.motion_base_path}")
        print(f"Pattern: {cfg.input.motion_pattern}")
        
        # Load dataset (needed for motion_idx and structure)
        dyer.load_dataset()
        
        # Load and encode original motions
        cached_latents = dyer.load_origin_motions()
        
        # Attach cached latents to dataset using motion_idx
        latents, valid_episodes = dyer.attach_cached_latents(cached_latents)
        
        # Save with filtering
        dyer.save_dataset(latents, valid_episodes=valid_episodes)
        
    else:
        print("\n" + "="*80)
        print("Using STANDARD DYEING mode")
        print("="*80)
        print(f"Loading collected dataset from: {cfg.input.zarr_path}")
        
        # Load dataset
        dyer.load_dataset()
        
        # Encode motions from collected samples
        latents = dyer.encode_motions()
    
        # Save dataset
        dyer.save_dataset(latents)


if __name__ == '__main__':
    main()
