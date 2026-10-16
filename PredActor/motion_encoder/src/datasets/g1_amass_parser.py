# -*- coding: utf-8 -*-

# G1 Retargeted AMASS Dataset Parser
# This parser processes G1 retargeted AMASS motion capture data instead of SMPL-based data.
# The G1 dataset contains robot-specific joint angles and body positions.

import joblib
import argparse
from tqdm import tqdm
import json
import os.path as osp
import os
import sys
import re
from pathlib import Path
sys.path.append('.')

import torch
import numpy as np
from PIL import Image
from src.datasets import g1_amass_utils
from src import config

comp_device = torch.device("cpu")

# G1 retargeted files have different suffix
G1_FILE_SUFFIX = '_jpos.npz'  # Instead of '_poses.npz'

# Same splits as original AMASS
all_sequences = [
    'ACCAD',
    'BioMotionLab_NTroje',
    'CMU',
    'EKUT',
    'Eyes_Japan_Dataset',
    'HumanEva',
    'KIT',
    'MPI_HDM05',
    'MPI_Limits',
    'MPI_mosh',
    'SFU',
    'SSM_synced',
    'TCD_handMocap',
    'TotalCapture',
    'Transitions_mocap',
]
amass_test_split = ['Transitions_mocap', 'SSM_synced']
amass_vald_split = ['HumanEva', 'MPI_HDM05', 'SFU', 'MPI_mosh']
amass_train_split = ['BioMotionLab_NTroje', 'Eyes_Japan_Dataset', 'TotalCapture', 'KIT', 'ACCAD', 'CMU', 'MPI_Limits',
                     'TCD_handMocap', 'EKUT']
amass_splits = {
    'test': amass_test_split,
    'vald': amass_vald_split,
    'train': amass_train_split
}
assert len(amass_splits['train'] + amass_splits['test'] + amass_splits['vald']) == len(all_sequences) == 15


def read_data(folder, split_name, dataset_name, target_fps, max_fps_dist, quick_run, babel_labels, clip_images_dir=None):
    """
    Read G1 retargeted AMASS dataset.
    
    Args:
        folder: Root directory containing G1 retargeted AMASS data
        split_name: 'train', 'vald', or 'test'
        dataset_name: 'amass' or 'babel'
        target_fps: Target frame rate (should be 30 for G1 data)
        max_fps_dist: Maximum allowed fps distance from target
        quick_run: If True, skip some processing for debugging
        babel_labels: Dictionary mapping filenames to BABEL annotations
        clip_images_dir: Optional directory containing rendered images
    
    Returns:
        Database dictionary with G1 motion data
    """
    if dataset_name == "amass":
        sequences = amass_splits[split_name]
    else:
        sequences = all_sequences

    db = {
        'vid_names': [],
        'dof_positions': [],              # G1 joint angles (29,)
        'body_positions': [],              # G1 body positions (30, 3)
        'dof_velocities': [],              # G1 joint velocities (29,)
        'body_rotations': [],              # G1 body orientations (30, 4) quaternions
        'body_linear_velocities': [],      # G1 body linear velocities (30, 3)
        'body_angular_velocities': [],     # G1 body angular velocities (30, 3)
        'clip_images': [],
        'clip_pathes': [],
        'text_raw_labels': [],
        'text_proc_labels': [],
        'action_cat': []
    }

    clip_images_path = clip_images_dir
    if clip_images_path is not None:
        assert os.path.isdir(clip_images_path), f"Clip images directory not found: {clip_images_path}"

    for seq_name in sequences:
        print(f'Reading {seq_name} sequence...')
        seq_folder = osp.join(folder, seq_name)
        if not osp.isdir(seq_folder):
            print(f'Skipping absent AMASS subset: {seq_name}')
            continue

        results_dict = read_single_sequence(
            split_name, dataset_name, seq_folder, seq_name,
            target_fps, max_fps_dist, quick_run,
            clip_images_path, babel_labels
        )

        for k in db.keys():
            db[k].extend(results_dict[k])

    return db


def read_single_sequence(split_name, dataset_name, folder, seq_name, target_fps, max_fps_dist,
                         quick_run, clip_images_path, fname_to_babel):
    """
    Read a single sequence from G1 retargeted AMASS dataset.
    
    The G1 files contain:
    - dof_positions: (T, 29) - joint angles in radians
    - dof_velocities: (T, 29) - joint velocities in rad/s
    - body_positions: (T, 30, 3) - 3D positions of robot bodies
    - body_rotations: (T, 30, 4) - quaternion orientations
    - body_linear_velocities: (T, 30, 3)
    - body_angular_velocities: (T, 30, 3)
    - dof_names: (29,) - joint names
    - body_names: (30,) - body names
    - fps: frame rate (should be 30.0)
    """
    subjects = sorted(name for name in os.listdir(folder) if osp.isdir(osp.join(folder, name)))

    dof_positions = []
    body_positions = []
    dof_velocities = []
    body_rotations = []
    body_linear_velocities = []
    body_angular_velocities = []
    vid_names = []
    clip_images = []
    clip_pathes = []
    text_raw_labels = []
    text_proc_labels = []
    action_cat = []

    # For each subject
    for subject in tqdm(subjects):
        # Look for G1 retargeted files (suffix: _jpos.npz)
        actions = sorted(x for x in os.listdir(osp.join(folder, subject)) if x.endswith(G1_FILE_SUFFIX))

        # For each action npz file
        for action in actions:
            fname = osp.join(folder, subject, action)

            # Map to BABEL annotations
            # Convert G1 filename back to original AMASS filename
            # E.g., "D2-Wait1_poses_120_jpos.npz" -> "D2-Wait1_poses.npz"
            original_action_name = re.sub(r'_(?:[0-9]+_)?jpos\.npz$', '.npz', action)
            folder_path, sequence_name = os.path.split(folder)
            seq_subj_action = osp.join(sequence_name, subject, original_action_name)
            
            # Try multiple name variations to match BABEL
            babel_dict = None
            # for name_variant in [seq_subj_action, 
            #                     seq_subj_action.replace('_poses.npz', '_poses.npz'),
            #                     seq_subj_action.replace('-', ' - ').replace('_poses', '_poses')]:
            #     if name_variant in fname_to_babel:
            #         babel_dict = fname_to_babel[name_variant]
            #         break
            
            if babel_dict is None:
                # Try with original naming convention
                if seq_subj_action in fname_to_babel:
                    babel_dict = fname_to_babel[seq_subj_action]
                else:
                    print(f"Not in BABEL: {seq_subj_action}")
                    continue

            if dataset_name == "babel":
                # Check if pose belongs to split
                babel_split = babel_dict['split'].replace("val", "vald")
                if babel_split != split_name:
                    continue

            # Load G1 retargeted data
            data = np.load(fname, allow_pickle=False)
            
            # Verify this is G1 data
            required = {'dof_positions', 'body_positions', 'fps'}
            if not required.issubset(data.files):
                raise ValueError(f'{fname}: expected G1 xyz schema keys {sorted(required)}; '
                                 f'missing {sorted(required - set(data.files))}')

            # Extract G1 motion data
            dof_pos = data['dof_positions']  # (T, 29)
            body_pos = data['body_positions']  # (T, 30, 3)
            if dof_pos.ndim != 2 or dof_pos.shape[1] != 29 or body_pos.shape != (len(dof_pos), 30, 3):
                raise ValueError(f'{fname}: expected dof_positions[T,29], body_positions[T,30,3]')
            if not np.isfinite(dof_pos).all() or not np.isfinite(body_pos).all():
                raise ValueError(f'{fname}: nonfinite motion values')
            if 'body_names' in data and data['body_names'].tolist() != g1_amass_utils.G1_BODY_NAMES:
                raise ValueError(f'{fname}: body_names must use the semantic G1 MotionCLIP order')
            dof_vel = data['dof_velocities'] if 'dof_velocities' in data else None  # (T, 29)
            body_rot = data['body_rotations'] if 'body_rotations' in data else None  # (T, 30, 4)
            body_lin_vel = data['body_linear_velocities'] if 'body_linear_velocities' in data else None  # (T, 30, 3)
            body_ang_vel = data['body_angular_velocities'] if 'body_angular_velocities' in data else None  # (T, 30, 3)
            
            # Get fps
            fps_data = np.asarray(data['fps']).reshape(-1)
            if fps_data.size != 1 or not np.isfinite(fps_data[0]) or fps_data[0] <= 0:
                raise ValueError(f'{fname}: fps must contain one positive finite number')
            fps = float(fps_data[0])
            data.close()
            
            duration_t = babel_dict['dur']
            
            # Seq. labels
            seq_raw_labels, seq_proc_label, seq_act_cat = [], [], []
            frame_raw_text_labels = np.full(dof_pos.shape[0], "", dtype=object)
            frame_proc_text_labels = np.full(dof_pos.shape[0], "", dtype=object)
            frame_action_cat = np.full(dof_pos.shape[0], "", dtype=object)

            for label_dict in (babel_dict.get('seq_ann') or {}).get('labels', []):
                seq_raw_labels.extend([label_dict['raw_label']])
                seq_proc_label.extend([label_dict['proc_label']])
                if label_dict['act_cat'] is not None:
                    seq_act_cat.extend(label_dict['act_cat'])

            # Frame labels (Assign labels to each frame)
            if babel_dict['frame_ann'] is None:
                if not seq_raw_labels:
                    print(f'Skipping motion without text annotations: {seq_subj_action}')
                    continue
                frame_raw_labels = "and ".join(seq_raw_labels)
                frame_proc_labels = "and ".join(seq_proc_label)
                start_frame = 0
                end_frame = dof_pos.shape[0]
                frame_raw_text_labels[start_frame:end_frame] = frame_raw_labels
                frame_proc_text_labels[start_frame:end_frame] = frame_proc_labels
                frame_action_cat[start_frame:end_frame] = ",".join(seq_act_cat)
            else:
                for label_dict in babel_dict['frame_ann']['labels']:
                    start_frame = round(label_dict['start_t'] * fps)
                    end_frame = round(label_dict['end_t'] * fps)
                    frame_raw_text_labels[start_frame:end_frame] = label_dict['raw_label']
                    frame_proc_text_labels[start_frame:end_frame] = label_dict['proc_label']
                    if label_dict['act_cat'] is not None:
                        frame_action_cat[start_frame:end_frame] = str(",".join(label_dict['act_cat']))

            # Handle target fps (G1 data is already at 30fps, so mainly for validation)
            if target_fps is not None:
                if abs(fps - target_fps) > max_fps_dist:
                    print(f'Skipping [{fps}]fps G1 seq, target_fps=[{target_fps}], max_fps_dist=[{max_fps_dist}]')
                    continue
                
                # If fps matches target, no resampling needed
                # G1 data is typically already at 30fps
                if abs(fps - target_fps) < 0.1:
                    # No resampling needed
                    sampling_freq = 1
                else:
                    # Calculate sampling frequency
                    sampling_freq = round(fps / target_fps)
                
                # FIXME: Use interpolation for better resampling?
                if sampling_freq > 1:
                    dof_pos = dof_pos[0::sampling_freq]
                    body_pos = body_pos[0::sampling_freq]
                    if dof_vel is not None:
                        dof_vel = dof_vel[0::sampling_freq]
                    if body_rot is not None:
                        body_rot = body_rot[0::sampling_freq]
                    if body_lin_vel is not None:
                        body_lin_vel = body_lin_vel[0::sampling_freq]
                    if body_ang_vel is not None:
                        body_ang_vel = body_ang_vel[0::sampling_freq]
                    frame_raw_text_labels = frame_raw_text_labels[0::sampling_freq]
                    frame_proc_text_labels = frame_proc_text_labels[0::sampling_freq]
                    frame_action_cat = frame_action_cat[0::sampling_freq]

            # Skip short sequences
            if dof_pos.shape[0] < 60:
                continue

            # Create video name
            vid_name = np.array([f'{seq_name}_{subject}_{action.replace(G1_FILE_SUFFIX, "")}']*dof_pos.shape[0])

            # Handle images (optional)
            if quick_run:
                images = None
                images_path = None
            else:
                images = None
                images_path = None
                if clip_images_path is not None:
                    images_path = [os.path.join(clip_images_path, f) for f in os.listdir(clip_images_path) 
                                 if f.startswith(vid_name[0][:-9]) and f.endswith('.png')]
                    if images_path:
                        images_path.sort(key=lambda x: int(x.replace('.png', '').split('frame')[-1]))
                        images_path = np.array(images_path)
                        images = [np.asarray(Image.open(im)) for im in images_path]
                        images = np.concatenate([np.expand_dims(im, 0) for im in images], axis=0)

            # Append to lists
            vid_names.append(vid_name)
            dof_positions.append(dof_pos)
            body_positions.append(body_pos)
            if dof_vel is not None:
                dof_velocities.append(dof_vel)
            else:
                dof_velocities.append(np.zeros_like(dof_pos))  # Placeholder if not available
            if body_rot is not None:
                body_rotations.append(body_rot)
            else:
                body_rotations.append(np.zeros((body_pos.shape[0], 30, 4)))  # Placeholder
            if body_lin_vel is not None:
                body_linear_velocities.append(body_lin_vel)
            else:
                body_linear_velocities.append(np.zeros_like(body_pos))  # Placeholder
            if body_ang_vel is not None:
                body_angular_velocities.append(body_ang_vel)
            else:
                body_angular_velocities.append(np.zeros_like(body_pos))  # Placeholder
            clip_images.append(images)
            clip_pathes.append(images_path)
            text_raw_labels.append(frame_raw_text_labels)
            text_proc_labels.append(frame_proc_text_labels)
            action_cat.append(frame_action_cat)

    return {
        'vid_names': vid_names,
        'dof_positions': dof_positions,
        'body_positions': body_positions,
        'dof_velocities': dof_velocities,
        'body_rotations': body_rotations,
        'body_linear_velocities': body_linear_velocities,
        'body_angular_velocities': body_angular_velocities,
        'clip_images': clip_images,
        'clip_pathes': clip_pathes,
        'text_raw_labels': text_raw_labels,
        'text_proc_labels': text_proc_labels,
        'action_cat': action_cat
    }


def get_babel_labels(babel_dir_path):
    """Load BABEL text annotations."""
    print("Loading babel labels")
    l_babel_dense_files = ['train', 'val']
    pose_file_to_babel = {}
    for file in l_babel_dense_files:
        path = os.path.join(babel_dir_path, file + '.json')
        with open(path) as stream:
            data = json.load(stream)
        for seq_id, seq_dict in data.items():
            npz_path = os.path.join(*(seq_dict['feat_p'].split(os.path.sep)[1:]))
            seq_dict['split'] = file
            pose_file_to_babel[npz_path] = seq_dict
    print("DONE! - Loading babel labels")
    print(f'Loaded {len(pose_file_to_babel)} annotated motion paths')
    return pose_file_to_babel


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, help='G1 retargeted AMASS dataset directory', 
                       default='./data/g1_retargeted_amass')
    parser.add_argument('--output_dir', type=str, help='target directory', 
                       default='./data/g1_amass_db')
    parser.add_argument('--clip_images_dir', type=str, help='rendered images directory', 
                       default=None)
    parser.add_argument('--target_fps', type=int, choices=[10, 30, 60], default=30,
                       help='Target FPS (G1 data is at 30fps)')
    parser.add_argument('--quick_run', action='store_true', 
                       help='Quick run for debugging without saving')
    parser.add_argument('--dataset_name', required=True, type=str, choices=['amass', 'babel'], 
                       default='amass', help='Dataset to create')
    parser.add_argument('--babel_dir', type=str, 
                       help='Path to BABEL annotations directory',
                       default='./data/babel_v1.0_release')
    parser.add_argument('--splits', nargs='+', choices=list(amass_splits),
                        default=list(amass_splits), help='Dataset splits to prepare')

    args = parser.parse_args()
    if not Path(args.input_dir).is_dir():
        parser.error(f'Input directory does not exist: {args.input_dir}')

    # Load BABEL labels
    fname_to_babel = get_babel_labels(args.babel_dir)

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    max_fps_dist = 5
    if args.quick_run:
        print('Quick run mode - no saving')

    print("=" * 60)
    print("G1 Retargeted AMASS Parser")
    print("=" * 60)
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Target FPS: {args.target_fps}")
    print(f"Dataset: {args.dataset_name}")
    print(f"G1 DOFs: {g1_amass_utils.G1_NUM_DOFS}")
    print(f"G1 Bodies: {g1_amass_utils.G1_NUM_BODIES}")
    print("=" * 60)

    for split_name in args.splits:
        print(f"\nProcessing split: {split_name}")
        db = read_data(
            args.input_dir,
            split_name=split_name,
            dataset_name=args.dataset_name,
            target_fps=args.target_fps,
            max_fps_dist=max_fps_dist,
            quick_run=args.quick_run,
            babel_labels=fname_to_babel,
            clip_images_dir=args.clip_images_dir
        )

        db_file = osp.join(args.output_dir, '{}_{}fps'.format(args.dataset_name, args.target_fps))
        db_file += '_{}.pt'.format(split_name)
        if not db['vid_names']:
            print(f'No annotated sequences for split {split_name}; no empty database saved')
            continue
        if os.path.exists(db_file) and not args.quick_run:
            raise FileExistsError(f'Dataset exists; choose a new output directory: {db_file}')
        
        if args.quick_run:
            print(f'Quick run mode - file would be saved to {db_file}')
            print(f'Processed {len(db["vid_names"])} sequences')
        else:
            print(f'Saving G1 AMASS dataset to {db_file}')
            joblib.dump(db, db_file)
            print(f'Successfully saved {len(db["vid_names"])} sequences')
    
    print("\n" + "=" * 60)
    print("G1 AMASS parsing complete!")
    print("=" * 60)
