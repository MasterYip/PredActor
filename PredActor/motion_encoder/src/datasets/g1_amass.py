"""G1 AMASS loader extracted from the G1 class added in commit 1cdfc7d."""

import os
import joblib
import numpy as np
from PIL import Image

from .dataset import Dataset
from src.utils.action_label_to_idx import idx_to_action_label


class G1AMASS(Dataset):
    """
    G1 Retargeted AMASS Dataset loader for robot motion data.
    
    Loads G1 retargeted AMASS data with:
    - body_positions: (T, 30, 3) - 3D positions of robot bodies (primary motion representation)
    - dof_positions: (T, 29) - joint angles in radians
    - dof_velocities: (T, 29) - joint velocities
    - body_rotations: (T, 30, 4) - quaternion orientations
    - body_linear_velocities: (T, 30, 3)
    - body_angular_velocities: (T, 30, 3)
    
    Args:
        datapath: Path to G1 dataset file (e.g., 'data/g1_amass_db/g1_amass_30fps_train.pt')
        split: Dataset split ('train', 'vald', or 'test')
        **kwargs: Additional arguments passed to parent Dataset class
        
    Example:
        dataset = G1AMASS(datapath='./data/g1_amass_db/g1_amass_30fps_db.pt', 
                         split='train', pose_rep='xyz')
    """
    dataname = "g1_amass"

    def __init__(self, datapath="data/g1_amass_db/g1_amass_30fps_db.pt", split="train", **kwargs):
        assert '_db.pt' in datapath
        self.datapath = datapath.replace('_db.pt', '_{}.pt'.format(split))
        assert os.path.exists(self.datapath), f"G1 AMASS dataset not found: {self.datapath}"
        print('G1 AMASS datapath: [{}]'.format(self.datapath))
        super().__init__(split='val' if split == 'vald' else split, **kwargs)

        self.dataname = "g1_amass"
        
        # G1 specific settings
        self.rot_convention = 'g1_xyz'  # Using body positions (xyz)
        self.use_betas = False  # G1 has fixed geometry
        self.use_gender = False  # Not applicable for robot
        self.use_body_features = False
        
        if 'clip_preprocess' in kwargs.keys():
            self.clip_preprocess = kwargs['clip_preprocess']

        dummy_class = [0]
        self.num_classes = len(dummy_class)

        self.db = self.load_db()
        
        # G1 specific data storage
        self._body_positions = []      # (T, 30, 3) - primary motion representation
        self._dof_positions = []       # (T, 29) - joint angles
        self._dof_velocities = []      # (T, 29) - joint velocities
        self._body_rotations = []      # (T, 30, 4) - quaternions
        self._body_linear_velocities = []   # (T, 30, 3)
        self._body_angular_velocities = []  # (T, 30, 3)
        
        # Common data storage (same as AMASS)
        self._poses = []  # Will store body_positions reshaped to (T, 30*3)
        self._num_frames_in_video = []
        self._actions = []
        self._clip_images = []
        self._clip_texts = []
        self._clip_pathes = []
        self._actions_cat = []
        
        self.clip_label_text = "text_raw_labels"

        seq_len = 100
        n_sequences = len(self.db['body_positions'])
        
        # Split sequences
        for seq_idx in range(n_sequences):
            # The list of All motions of all Sequences & subjects
            body_pos = self.db['body_positions'][seq_idx]
            n_sub_seq = body_pos.shape[0] // seq_len
            if n_sub_seq == 0:
                continue
            n_frames_in_use = n_sub_seq * seq_len
            
            # Split body positions (primary data)
            body_positions = np.split(body_pos[:n_frames_in_use], n_sub_seq)
            self._body_positions.extend(body_positions)
            
            # Reshape body positions to (T, 90) for compatibility with pose representation
            poses_flat = [bp.reshape(seq_len, -1) for bp in body_positions]
            self._poses.extend(poses_flat)
            
            # Split DOF positions
            if 'dof_positions' in self.db:
                dof_pos = np.split(self.db['dof_positions'][seq_idx][:n_frames_in_use], n_sub_seq)
                self._dof_positions.extend(dof_pos)
            
            # Split DOF velocities
            if 'dof_velocities' in self.db:
                dof_vel = np.split(self.db['dof_velocities'][seq_idx][:n_frames_in_use], n_sub_seq)
                self._dof_velocities.extend(dof_vel)
            
            # Split body rotations
            if 'body_rotations' in self.db:
                body_rot = np.split(self.db['body_rotations'][seq_idx][:n_frames_in_use], n_sub_seq)
                self._body_rotations.extend(body_rot)
            
            # Split body linear velocities
            if 'body_linear_velocities' in self.db:
                body_lin_vel = np.split(self.db['body_linear_velocities'][seq_idx][:n_frames_in_use], n_sub_seq)
                self._body_linear_velocities.extend(body_lin_vel)
            
            # Split body angular velocities
            if 'body_angular_velocities' in self.db:
                body_ang_vel = np.split(self.db['body_angular_velocities'][seq_idx][:n_frames_in_use], n_sub_seq)
                self._body_angular_velocities.extend(body_ang_vel)
            
            self._num_frames_in_video.extend([seq_len] * n_sub_seq)
            
            # Action categories
            if 'action_cat' in self.db:
                self._actions_cat.extend(np.split(self.db['action_cat'][seq_idx][:n_frames_in_use], n_sub_seq))
            
            # CLIP data
            if 'clip_images' in self.db.keys() and self.db['clip_images'][seq_idx] is not None:
                images = [np.squeeze(e) for e in np.split(self.db['clip_images'][seq_idx][:n_sub_seq], n_sub_seq)]
                processed_images = [self.clip_preprocess(Image.fromarray(img)) for img in images]
                self._clip_images.extend(processed_images)
            
            if self.clip_label_text in self.db:
                self._clip_texts.extend(np.split(self.db[self.clip_label_text][seq_idx][:n_frames_in_use], n_sub_seq))
            
            if 'clip_pathes' in self.db:
                self._clip_pathes.extend(np.split(self.db['clip_pathes'][seq_idx][:n_sub_seq], n_sub_seq))
            
            # Dummy actions
            actions = [0] * n_sub_seq
            self._actions.extend(actions)

        assert len(self._num_frames_in_video) == len(self._poses) == len(self._body_positions) == len(self._actions)
        
        self._actions = np.array(self._actions)
        self._num_frames_in_video = np.array(self._num_frames_in_video)

        N = len(self._poses)
        if N == 0:
            raise ValueError("G1 AMASS database contains no sequences with at least 100 frames")
        self._train = np.arange(N)
        self._test = np.arange(N)

        self._action_to_label = {x: i for i, x in enumerate(dummy_class)}
        self._label_to_action = {i: x for i, x in enumerate(dummy_class)}

        self._action_classes = idx_to_action_label
        
        print(f'G1AMASS dataset loaded: {N} sequences, {sum(self._num_frames_in_video)} frames total')

    def load_db(self):
        """Load G1 retargeted AMASS dataset from .pt file."""
        db_file = self.datapath
        db = joblib.load(db_file)

        for key in ('clip_images', 'clip_pathes'):
            if key in db and all(value is None for value in db[key]):
                del db[key]

        return db

    # Legacy Support
    def _load_joints3D(self, ind, frame_ix):
        """Load 3D body positions (equivalent to joints3D for G1)."""
        body_pos = self._body_positions[ind][frame_ix]  # (30, 3)
        return body_pos

    def _load_rotvec(self, ind, frame_ix):
        """
        Load rotation vectors for G1.
        For G1, we return body_positions reshaped to match expected format.
        Shape: (seq_len, 30, 3)
        """
        body_pos = self._body_positions[ind][frame_ix]  # (30, 3)
        # Reshape to (30, 1, 3) to match expected format (num_bodies, 1, 3)
        return body_pos.reshape(30, 1, 3)

    # New G1-specific loaders
    def _load_dof_positions(self, ind, frame_ix):
        """Load DOF positions for G1 robot."""
        if len(self._dof_positions) > 0:
            return self._dof_positions[ind][frame_ix]
        return None

    def _load_dof_velocities(self, ind, frame_ix):
        """Load DOF velocities for G1 robot."""
        if len(self._dof_velocities) > 0:
            return self._dof_velocities[ind][frame_ix]
        return None

    def _load_body_positions(self, ind, frame_ix):
        """Load 3D body positions (equivalent to joints3D for G1)."""
        if len(self._body_positions) > 0:
            return self._body_positions[ind][frame_ix]  # (30, 3)
        return None

    def _load_body_linear_velocities(self, ind, frame_ix):
        """Load body linear velocities for G1 robot."""
        if len(self._body_linear_velocities) > 0:
            return self._body_linear_velocities[ind][frame_ix]
        return None

    def _load_body_rotations(self, ind, frame_ix):
        """Load body rotations (quaternions) for G1 robot."""
        if len(self._body_rotations) > 0:
            return self._body_rotations[ind][frame_ix]
        return None

    def _load_body_angular_velocities(self, ind, frame_ix):
        """Load body angular velocities for G1 robot."""
        if len(self._body_angular_velocities) > 0:
            return self._body_angular_velocities[ind][frame_ix]
        return None
