"""Prepare captioned G1 motions in the encoder's original xyz representation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from src.datasets.g1_amass_utils import G1_BODY_NAMES


ISAACLAB_BODY_NAMES = [
    'pelvis', 'left_hip_pitch_link', 'right_hip_pitch_link', 'waist_yaw_link',
    'left_hip_roll_link', 'right_hip_roll_link', 'waist_roll_link',
    'left_hip_yaw_link', 'right_hip_yaw_link', 'torso_link', 'left_knee_link',
    'right_knee_link', 'left_shoulder_pitch_link', 'right_shoulder_pitch_link',
    'left_ankle_pitch_link', 'right_ankle_pitch_link', 'left_shoulder_roll_link',
    'right_shoulder_roll_link', 'left_ankle_roll_link', 'right_ankle_roll_link',
    'left_shoulder_yaw_link', 'right_shoulder_yaw_link', 'left_elbow_link',
    'right_elbow_link', 'left_wrist_roll_link', 'right_wrist_roll_link',
    'left_wrist_pitch_link', 'right_wrist_pitch_link', 'left_wrist_yaw_link',
    'right_wrist_yaw_link',
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_positions(path: Path, body_order: str, start: int = 0, end: int | None = None):
    with np.load(path, allow_pickle=False) as source:
        key = 'body_pos_w' if 'body_pos_w' in source else 'body_positions'
        positions = np.asarray(source[key], dtype=np.float32)
        fps = float(np.asarray(source['fps']).reshape(-1)[0])
        if 'body_names' in source:
            names = [str(name) for name in source['body_names']]
        elif body_order == 'isaaclab':
            names = ISAACLAB_BODY_NAMES
        elif body_order == 'motionclip':
            names = G1_BODY_NAMES
        else:
            raise ValueError('Specify body_order as isaaclab or motionclip when body_names is absent')
    if positions.ndim != 3 or positions.shape[1:] != (30, 3):
        raise ValueError(f'{path}: expected [T,30,3], got {positions.shape}')
    if not np.isfinite(positions).all() or not np.isfinite(fps) or fps <= 0:
        raise ValueError(f'{path}: nonfinite positions or invalid fps')
    if len(names) != 30 or set(names) != set(G1_BODY_NAMES):
        raise ValueError(f'{path}: body_names must contain each G1 body exactly once')
    end = len(positions) if end is None else end
    if not 0 <= start < end <= len(positions):
        raise ValueError(f'{path}: invalid frame interval [{start}, {end})')
    return positions[start:end, [names.index(name) for name in G1_BODY_NAMES]], fps


def resample(positions: np.ndarray, fps: float, target_fps: float) -> np.ndarray:
    if not np.isfinite(target_fps) or target_fps <= 0:
        raise ValueError('target_fps must be positive')
    old_time = np.arange(len(positions), dtype=np.float64) / fps
    new_time = np.arange(int(np.floor(old_time[-1] * target_fps)) + 1) / target_fps
    flat = positions.reshape(len(positions), -1)
    return np.stack([np.interp(new_time, old_time, flat[:, i]) for i in range(90)], axis=1).reshape(-1, 30, 3).astype(np.float32)


def prepare(annotations: Path, output: Path, *, frames: int = 60, stride: int = 30,
            target_fps: float = 30.0) -> dict:
    if frames < 2 or stride < 1:
        raise ValueError('frames must be >=2 and stride >=1')
    records = json.loads(annotations.read_text())
    if not isinstance(records, list) or not records:
        raise ValueError('annotations must be a nonempty JSON list')
    windows, captions, provenance = [], [], []
    for record in records:
        text = record.get('text')
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Every annotation requires a nonempty human-provided text caption')
        path = (annotations.parent / record['motion']).resolve(strict=True)
        positions, fps = load_positions(path, record.get('body_order', ''),
                                        record.get('start_frame', 0), record.get('end_frame'))
        positions = resample(positions, fps, target_fps)
        if len(positions) < frames:
            raise ValueError(f'{path}: {len(positions)} resampled frames, need at least {frames}')
        count = 0
        for first in range(0, len(positions) - frames + 1, stride):
            window = positions[first:first + frames].copy()
            # Match the original G1 Dataset._load: first-frame pelvis centering.
            window -= window[0, 0].copy()
            windows.append(window.transpose(1, 2, 0))
            captions.append(text.strip())
            count += 1
        provenance.append({'motion': record['motion'], 'sha256': sha256(path),
                           'source_fps': fps, 'windows': count, 'text': text.strip(),
                           'body_order': record.get('body_order', 'names-in-npz'),
                           'start_frame': record.get('start_frame', 0), 'end_frame': record.get('end_frame')})
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    with output.open('xb') as stream:
        np.savez_compressed(stream, x=np.stack(windows), text=np.asarray(captions))
    report = {'format_version': 1, 'shape': [len(windows), 30, 3, frames],
              'target_fps': target_fps, 'stride': stride, 'source': provenance,
              'dataset_sha256': sha256(output)}
    output.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


class CaptionedMotions(Dataset):
    def __init__(self, path: Path):
        with np.load(path, allow_pickle=False) as source:
            self.x = torch.from_numpy(source['x'].astype(np.float32))
            self.text = source['text'].tolist()
        if self.x.ndim != 4 or self.x.shape[1:3] != (30, 3) or self.x.shape[3] < 2:
            raise ValueError('Prepared x must have shape [N,30,3,T] with T>=2')
        if len(self.x) == 0 or len(self.text) != len(self.x) or not torch.isfinite(self.x).all():
            raise ValueError('Invalid prepared motion/text data')
        if not all(isinstance(text, str) and text.strip() for text in self.text):
            raise ValueError('Prepared captions must be nonempty strings')

    def __len__(self):
        return len(self.x)

    def __getitem__(self, index):
        frames = self.x.shape[-1]
        return {'x': self.x[index], 'clip_text': self.text[index], 'y': torch.tensor(0),
                'lengths': torch.tensor(frames), 'mask': torch.ones(frames, dtype=torch.bool)}
