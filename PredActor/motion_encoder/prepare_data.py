"""Prepare explicitly captioned G1 motion windows for MotionCLIP fine-tuning."""

import argparse
import json
from pathlib import Path

from src.finetuning.data import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frames', type=int, default=60)
    parser.add_argument('--stride', type=int, default=30)
    parser.add_argument('--target-fps', type=float, default=30.0)
    args = parser.parse_args()
    print(json.dumps(prepare(args.annotations, args.output, frames=args.frames,
                             stride=args.stride, target_fps=args.target_fps), indent=2))


if __name__ == '__main__':
    main()
