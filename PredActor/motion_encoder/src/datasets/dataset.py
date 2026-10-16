import random
import numpy as np
import torch
from .tools import parse_info_name
from ..utils.tensors import collate
from ..utils.misc import to_torch

POSE_REPS = ["xyz", "rotvec", "rotmat", "rotquat", "rot6d", "posquat", "posvel"]
UNSUPERVISED_BABEL_ACTION_CAT_LABELS_IDXS = [48, 50, 28, 38, 52, 11, 29, 19, 51, 22, 14, 21, 26, 10, 24]
from src.utils.action_label_to_idx import action_label_to_idx


class Dataset(torch.utils.data.Dataset):
    """
    Base dataset class for motion data.
    
    Supports both SMPL-based human poses and G1 robot DOF positions.
    
    Args:
        num_frames: Number of frames per sequence (-1 for variable length)
        sampling: Sampling strategy ('conseq', 'random_conseq', 'random')
        sampling_step: Step size for consecutive sampling
        split: Dataset split ('train', 'val', or 'test')
        pose_rep: Pose representation ('xyz', 'rotvec', 'rotmat', 'rotquat', 'rot6d')
                  Note: For G1 data, this is ignored and DOF positions are used directly
        translation: Whether to include translation
        glob: Whether to include global orientation
        max_len: Maximum sequence length (-1 for no limit)
        min_len: Minimum sequence length (-1 for no limit)
        num_seq_max: Maximum number of sequences (-1 for no limit)
        use_g1: If True, treats data as G1 DOF positions (default: False)
    """
    def __init__(self, num_frames=1, sampling="conseq", sampling_step=1, split="train",
                 pose_rep="rot6d", translation=True, glob=True, max_len=-1, min_len=-1, num_seq_max=-1, **kwargs):
        self.num_frames = num_frames
        self.sampling = sampling
        self.sampling_step = sampling_step
        self.split = split
        self.pose_rep = pose_rep
        self.translation = translation
        self.glob = glob
        self.max_len = max_len
        self.min_len = min_len
        self.num_seq_max = num_seq_max
        self.use_g1 = kwargs.get('use_g1', False)

        self.use_action_cat_as_text_labels = kwargs.get('use_action_cat_as_text_labels', False)
        self.only_60_classes = kwargs.get('only_60_classes', False)
        self.leave_out_15_classes = kwargs.get('leave_out_15_classes', False)
        self.use_only_15_classes = kwargs.get('use_only_15_classes', False)

        if self.split not in ["train", "val", "test"]:
            raise ValueError(f"{self.split} is not a valid split")

        super().__init__()

        # to remove shuffling
        self._original_train = None
        self._original_test = None

    def action_to_label(self, action):
        return self._action_to_label[action]

    def label_to_action(self, label):
        import numbers
        if isinstance(label, numbers.Integral):
            return self._label_to_action[label]
        else:  # if it is one hot vector
            label = np.argmax(label)
            return self._label_to_action[label]

    def get_pose_data(self, data_index, frame_ix):
        pose = self._load(data_index, frame_ix)
        label = self.get_label(data_index)
        return pose, label

    def get_clip_image(self, ind):
        clip_image = self._clip_images[ind]
        return clip_image

    def get_clip_path(self, ind):
        clip_path = self._clip_pathes[ind]
        return clip_path

    def get_clip_text(self, ind, frame_ix):
        clip_text = self._clip_texts[ind][frame_ix]
        return clip_text

    def get_clip_action_cat(self, ind, frame_ix):
        actions_cat = self._actions_cat[ind][frame_ix]
        return actions_cat

    def get_label(self, ind):
        action = self.get_action(ind)
        return self.action_to_label(action)

    def parse_action(self, path, return_int=True):
        info = parse_info_name(path)["A"]
        if return_int:
            return int(info)
        else:
            return info

    def get_action(self, ind):
        return self._actions[ind]

    def action_to_action_name(self, action):
        return self._action_classes[action]

    def label_to_action_name(self, label):
        action = self.label_to_action(label)
        return self.action_to_action_name(action)

    def __getitem__(self, index):
        if self.split == 'train':
            data_index = self._train[index]
        else:
            data_index = self._test[index]

        return self._get_item_data_index(data_index)

    def _load(self, ind, frame_ix):
        """
        Load motion data for a specific sequence and convert to desired representation.
        
        Args:
            ind: Data index in the dataset
            frame_ix: Frame indices to extract from the sequence
            
        Returns:
            Motion tensor in shape [num_joints/bodies, feat_dim, seq_len]
            - For G1: [30, 3, seq_len] (30 body positions, xyz)
            - For SMPL xyz: [22, 3, seq_len] (22 joints, xyz)
            - For SMPL rot6d+trans: [23, 9, seq_len] (22 joints + 1 translation, 6D rotation + 3D padding)
        """
        pose_rep = self.pose_rep
        if pose_rep != "xyz":
            import src.utils.rotation_conversions as geometry
        
        # ========== BLOCK 1: G1 Robot Data Loading ==========
        # For G1 retargeted data: use body positions directly (no rotation conversion needed)
        if self.use_g1:
            # Alternative: Load DOF positions (joint angles) - currently commented out
            # if getattr(self, "_load_dof_positions", None) is not None:
            #     dof_pos = self._load_dof_positions(ind, frame_ix)
            #     ret = to_torch(dof_pos)  # [seq_len, num_dofs=29]
            #     # Reshape to [num_dofs, 1, seq_len] for consistency with other representations
            #     ret = ret.unsqueeze(1).permute(1, 2, 0).contiguous()
            #     return ret.float()
            
            # Load body positions (30 rigid bodies, each with xyz position)
            if pose_rep == "xyz" or self.translation:
                if getattr(self, "_load_body_positions", None) is not None:
                    body_pos = self._load_body_positions(ind, frame_ix)  
                    # Shape: [seq_len, num_bodies=30, 3]
                    ret = to_torch(body_pos)
                    ret = ret - ret[0, 0, :]  # Center at root body position of first frame
                    # Shape: [seq_len, 30, 3]
                    if self.translation:
                        ret_tr = ret[:, 0, :]  # Root body trajectory
                        # Shape: [seq_len, 3]

            if pose_rep == "rot6d":
                body_quat = self._load_body_rotations(ind, frame_ix)
                # Shape: [seq_len, num_bodies=30, 4] (quaternions)
                body_rotmat = geometry.quaternion_to_matrix(to_torch(body_quat))
                # Shape: [seq_len, 30, 3, 3]
                ret = geometry.matrix_to_rotation_6d(body_rotmat)
                # Shape: [seq_len, 30, 6]

            if pose_rep == "posquat":
                body_pos = self._load_body_positions(ind, frame_ix)
                ret_pos = to_torch(body_pos)
                ret_pos = ret_pos - ret_pos[0, 0, :]  # Center at root body position of first frame
                # Shape: [seq_len, 30, 3]
                body_quat = self._load_body_rotations(ind, frame_ix)
                # Shape: [seq_len, num_bodies=30, 4] (quaternions)
                ret_rot = to_torch(body_quat)
                ret = torch.cat((ret_pos, ret_rot), 2)
                # Shape: [seq_len, 30, 7]

            if pose_rep == "posvel":
                body_pos = self._load_body_positions(ind, frame_ix)
                body_vel = self._load_body_linear_velocities(ind, frame_ix)
                ret_pos = to_torch(body_pos)
                ret_pos = ret_pos - ret_pos[0, 0, :]  # Center at root body position of first frame
                # Shape: [seq_len, 30, 3]
                ret_vel = to_torch(body_vel)
                # Shape: [seq_len, 30, 3]
                ret = torch.cat((ret_pos, ret_vel), 2)

            # Add translation if needed
            if pose_rep != "xyz" and self.translation:
                padded_tr = torch.zeros((ret.shape[0], ret.shape[2]), dtype=ret.dtype)
                # Shape: [seq_len, feat_dim] where feat_dim = 3, 4, 6, or 9
                padded_tr[:, :3] = ret_tr
                # Fill first 3 dims with actual translation (xyz), rest are zeros
                # Shape: [seq_len, feat_dim] with [x, y, z, 0, 0, ...] per frame
                ret = torch.cat((ret, padded_tr[:, None]), 1)

            ret = ret.permute(1, 2, 0).contiguous()  
            # Shape: [30, 3, seq_len]
            # Permute to standard format: [bodies, features, time]
            return ret.float()
        else:
            # ========== XYZ Joint Positions / Translation Loading ==========
            # Load 3D joint positions (for "xyz" representation or when translation is needed)
            if pose_rep == "xyz" or self.translation:
                if getattr(self, "_load_joints3D", None) is not None:
                    # Load raw 3D joint positions
                    joints3D = self._load_joints3D(ind, frame_ix)
                    # Shape: [seq_len, num_joints=22, 3]
                    
                    # Center the skeleton: subtract root joint position at first frame
                    # This removes global translation, keeping only relative positions
                    joints3D = joints3D - joints3D[0, 0, :]  
                    # Shape: [seq_len, 22, 3] (now centered at origin)
                    
                    ret = to_torch(joints3D)
                    # Shape: [seq_len, 22, 3]
                    
                    if self.translation:
                        # Extract root joint trajectory for separate translation handling
                        ret_tr = ret[:, 0, :]  
                        # Shape: [seq_len, 3] - root joint xyz over time
                else:
                    # Fallback: load translation separately if joints3D not available
                    if pose_rep == "xyz":
                        raise ValueError("This representation is not possible.")
                    if getattr(self, "_load_translation") is None:
                        raise ValueError("Can't extract translations.")
                    ret_tr = self._load_translation(ind, frame_ix)
                    # Shape: [seq_len, 3]
                    
                    ret_tr = to_torch(ret_tr - ret_tr[0])
                    # Shape: [seq_len, 3] (centered: first frame at origin)

            # ========== Rotation Representation Loading & Conversion ==========
            # Load and convert rotation data (for non-xyz representations)
            if pose_rep != "xyz":
                if getattr(self, "_load_rotvec", None) is None:
                    raise ValueError("This representation is not possible.")
                else:
                    # Load rotation vectors (axis-angle representation)
                    pose = self._load_rotvec(ind, frame_ix)
                    # Shape: [seq_len, num_joints=22, 3] (axis-angle for each joint)
                    
                    if not self.glob:
                        # Remove global orientation (root joint rotation) if glob=False
                        pose = pose[:, 1:, :]
                        # Shape: [seq_len, 21, 3] (without root joint)
                    
                    pose = to_torch(pose)
                    # Shape: [seq_len, 22 or 21, 3]
                    
                    # Convert axis-angle to desired rotation representation
                    if pose_rep == "rotvec":
                        ret = pose
                        # Shape: [seq_len, num_joints, 3] - keep as axis-angle
                        
                    elif pose_rep == "rotmat":
                        # Convert to rotation matrices (3x3 = 9 elements flattened)
                        ret = geometry.axis_angle_to_matrix(pose).view(*pose.shape[:2], 9)
                        # Shape: [seq_len, num_joints, 9]
                        
                    elif pose_rep == "rotquat":
                        # Convert to quaternions (4 elements: w, x, y, z)
                        ret = geometry.axis_angle_to_quaternion(pose)
                        # Shape: [seq_len, num_joints, 4]
                        
                    elif pose_rep == "rot6d":
                        # Convert to 6D rotation representation (continuous, good for learning)
                        ret = geometry.matrix_to_rotation_6d(geometry.axis_angle_to_matrix(pose))
                        # Shape: [seq_len, num_joints, 6]
            
            # ========== BLOCK 4: Add Translation to Rotation Data ==========
            # Concatenate translation with rotation data (if needed)
            if pose_rep != "xyz" and self.translation:
                # Create padded translation vector matching rotation feature dimension
                padded_tr = torch.zeros((ret.shape[0], ret.shape[2]), dtype=ret.dtype)
                # Shape: [seq_len, feat_dim] where feat_dim = 3, 4, 6, or 9
                
                padded_tr[:, :3] = ret_tr
                # Fill first 3 dims with actual translation (xyz), rest are zeros
                # Shape: [seq_len, feat_dim] with [x, y, z, 0, 0, ...] per frame
                
                ret = torch.cat((ret, padded_tr[:, None]), 1)
                # Shape: [seq_len, num_joints+1, feat_dim]
                # Concatenate translation as an extra "joint" channel
                # e.g., for rot6d: [seq_len, 23, 6] = 22 joints + 1 translation vector
            
            # ========== BLOCK 5: Final Permutation to Standard Format ==========
            # Permute from [seq_len, num_joints, feat_dim] to [num_joints, feat_dim, seq_len]
            ret = ret.permute(1, 2, 0).contiguous()
            # Shape: [num_joints, feat_dim, seq_len]
            # Standard format: [spatial, features, temporal]
            
            return ret.float()

    def _get_item_data_index(self, data_index):
        nframes = self._num_frames_in_video[data_index]

        if self.num_frames == -1 and (self.max_len == -1 or nframes <= self.max_len):
            frame_ix = np.arange(nframes)
        else:
            if self.num_frames == -2:
                if self.min_len <= 0:
                    raise ValueError("You should put a min_len > 0 for num_frames == -2 mode")
                if self.max_len != -1:
                    max_frame = min(nframes, self.max_len)
                else:
                    max_frame = nframes

                num_frames = random.randint(self.min_len, max(max_frame, self.min_len))
            else:
                num_frames = self.num_frames if self.num_frames != -1 else self.max_len
            # sampling goal: input: ----------- 11 nframes
            #                       o--o--o--o- 4  ninputs
            #
            # step number is computed like that: [(11-1)/(4-1)] = 3
            #                   [---][---][---][-
            # So step = 3, and we take 0 to step*ninputs+1 with steps
            #                   [o--][o--][o--][o-]
            # then we can randomly shift the vector
            #                   -[o--][o--][o--]o
            # If there are too much frames required
            if num_frames > nframes:
                fair = False  # True
                if fair:
                    # distills redundancy everywhere
                    choices = np.random.choice(range(nframes),
                                               num_frames,
                                               replace=True)
                    frame_ix = sorted(choices)
                else:
                    # adding the last frame until done
                    ntoadd = max(0, num_frames - nframes)
                    lastframe = nframes - 1
                    padding = lastframe * np.ones(ntoadd, dtype=int)
                    frame_ix = np.concatenate((np.arange(0, nframes),
                                               padding))

            elif self.sampling in ["conseq", "random_conseq"]:
                step_max = (nframes - 1) // (num_frames - 1)
                if self.sampling == "conseq":
                    if self.sampling_step == -1 or self.sampling_step * (num_frames - 1) >= nframes:
                        step = step_max
                    else:
                        step = self.sampling_step
                elif self.sampling == "random_conseq":
                    step = random.randint(1, step_max)

                lastone = step * (num_frames - 1)
                shift_max = nframes - lastone - 1
                shift = random.randint(0, max(0, shift_max - 1))
                frame_ix = shift + np.arange(0, lastone + 1, step)

            elif self.sampling == "random":
                choices = np.random.choice(range(nframes),
                                           num_frames,
                                           replace=False)
                frame_ix = sorted(choices)

            else:
                raise ValueError("Sampling not recognized.")

        inp, target = self.get_pose_data(data_index, frame_ix)

        output = {'inp': inp, 'target': target}
        if hasattr(self, 'db') and 'clip_images' in self.db.keys():
            output['clip_image'] = self.get_clip_image(data_index)

        if hasattr(self, 'db') and 'clip_pathes' in self.db.keys():
            output['clip_path'] = self.get_clip_path(data_index)

        if hasattr(self, 'db') and self.clip_label_text in self.db.keys():
            text_labels = self.get_clip_text(data_index, frame_ix)
            # Perform unique combination of text labels of each frame
            text_labels = " and ".join(list(np.unique(text_labels)))
            output['clip_text'] = text_labels

        if hasattr(self, 'db') and 'action_cat' in self.db.keys() and self.use_action_cat_as_text_labels:
            categories = self.get_clip_action_cat(data_index, frame_ix)
            unique_cats = np.unique(categories)
            all_valid_cats = []
            for multi_cats in unique_cats:
                for cat in multi_cats.split(","):
                    if cat not in action_label_to_idx:
                        continue
                    cat_idx = action_label_to_idx[cat]
                    if (cat_idx >= 120) or (self.only_60_classes and cat_idx >= 60) or (self.leave_out_15_classes and cat_idx in UNSUPERVISED_BABEL_ACTION_CAT_LABELS_IDXS):
                        continue
                    if self.use_only_15_classes and (cat_idx not in UNSUPERVISED_BABEL_ACTION_CAT_LABELS_IDXS):
                        continue
                    all_valid_cats.extend([cat])

            if len(all_valid_cats) == 0:  # No valid category available
                return None

            choosen_cat = np.random.choice(all_valid_cats, size=1)[0]
            # Replace clip text
            output['clip_text'] = choosen_cat
            output['y'] = action_label_to_idx[choosen_cat]
            output['all_categories'] = all_valid_cats

        return output

    def get_label_sample(self, label, n=1, return_labels=False, return_index=False):
        if self.split == 'train':
            index = self._train
        else:
            index = self._test

        action = self.label_to_action(label)
        choices = np.argwhere(np.array(self._actions)[index] == action).squeeze(1)

        if self.dataname == 'amass':
            if n == 1:
                while True:
                    idx = np.random.randint(0, len(self))
                    data = self._get_item_data_index(idx)
                    if data is None:
                        continue
                    x, y = data['inp'], data['target']
                    if y == label:
                        break
            else:
                x = []
                data_index = []
                while len(x) < n:
                    idx = np.random.randint(0, len(self))
                    data = self._get_item_data_index(idx)
                    x_inp, y = data['inp'], data['target']
                    if y == label:
                        x.append(x_inp)
                        data_index.append(idx)
                x = np.stack(x)
                y = label * np.ones(n, dtype=int)
        else:
            if n == 1:
                data_index = index[np.random.choice(choices)]
                data = self._get_item_data_index(data_index)
                x, y = data['inp'], data['target']
                assert (label == y)
                y = label
            else:
                data_index = np.random.choice(choices, n)
                x = np.stack([self._get_item_data_index(index[di])['inp'] for di in data_index])
                y = label * np.ones(n, dtype=int)
        if return_labels:
            if return_index:
                return x, y, data_index
            return x, y
        else:
            if return_index:
                return x, data_index
            return x

    def get_label_sample_batch(self, labels):
        samples = [self.get_label_sample(label, n=1, return_labels=True, return_index=False) for label in labels]
        samples = [{'inp': x[0], 'target': x[1]} for x in samples]  # Fix this to adapt new collate func
        batch = collate(samples)
        x = batch["x"]
        mask = batch["mask"]
        lengths = mask.sum(1)
        return x, mask, lengths

    def get_mean_length_label(self, label):
        if self.num_frames != -1:
            return self.num_frames

        if self.split == 'train':
            index = self._train
        else:
            index = self._test

        action = self.label_to_action(label)
        choices = np.argwhere(self._actions[index] == action).squeeze(1)
        lengths = self._num_frames_in_video[np.array(index)[choices]]

        if self.max_len == -1:
            return np.mean(lengths)
        else:
            # make the lengths less than max_len
            lengths[lengths > self.max_len] = self.max_len
        return np.mean(lengths)

    def get_stats(self):
        if self.split == 'train':
            index = self._train
        else:
            index = self._test

        numframes = self._num_frames_in_video[index]
        allmeans = np.array([self.get_mean_length_label(x) for x in range(self.num_classes)])

        stats = {"name": self.dataname,
                 "number of classes": self.num_classes,
                 "number of sequences": len(self),
                 "duration: min": int(numframes.min()),
                 "duration: max": int(numframes.max()),
                 "duration: mean": int(numframes.mean()),
                 "duration mean/action: min": int(allmeans.min()),
                 "duration mean/action: max": int(allmeans.max()),
                 "duration mean/action: mean": int(allmeans.mean())}
        return stats

    def __len__(self):
        num_seq_max = getattr(self, "num_seq_max", -1)
        if num_seq_max == -1:
            from math import inf
            num_seq_max = inf

        if self.split == 'train':
            return min(len(self._train), num_seq_max)
        else:
            return min(len(self._test), num_seq_max)

    def __repr__(self):
        return f"{self.dataname} dataset: ({len(self)}, _, ..)"

    def update_parameters(self, parameters):
        for i in range(len(self)):
            if self[i] is not None:
                self.njoints, self.nfeats, _ = self[i]['inp'].shape
                break
        parameters["num_classes"] = self.num_classes
        parameters["nfeats"] = self.nfeats
        parameters["njoints"] = self.njoints

    def shuffle(self):
        if self.split == 'train':
            random.shuffle(self._train)
        else:
            random.shuffle(self._test)

    def reset_shuffle(self):
        if self.split == 'train':
            if self._original_train is None:
                self._original_train = self._train
            else:
                self._train = self._original_train
        else:
            if self._original_test is None:
                self._original_test = self._test
            else:
                self._test = self._original_test
