"""Fine-tune the released G1 xyz MotionCLIP encoder and decoder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import clip
import torch
from torch.utils.data import DataLoader

from src.finetuning.data import CaptionedMotions, sha256
from src.models.get_model import get_model


def load_checkpoint(path: Path):
    return torch.load(path, map_location='cpu', weights_only=True)


def build_model(device: str, frames: int = 60):
    clip_model, _ = clip.load('ViT-B/32', device=device, jit=False)
    clip_model.eval().requires_grad_(False)
    parameters = dict(
        modeltype='cvae', njoints=30, nfeats=3, num_frames=frames,
        num_classes=1, translation=True, pose_rep='xyz', glob=True,
        glob_rot=[3.141592653589793, 0, 0], latent_dim=512, ff_size=1024,
        num_layers=8, num_heads=4, dropout=0.1, activation='gelu',
        device=device, lambdas={'rc': 100.0, 'rcxyz': 100.0, 'vel': 100.0},
        jointstype='vertices', vertstrans=False, use_g1=True, clip_training='',
        clip_lambdas={'text': {'cosine': 1.0}},
    )
    return get_model(parameters, clip_model)


def initialize(model, payload):
    state = payload.get('model', payload)
    # Historical frozen-CLIP training omitted CLIP weights; the official model
    # loaded above supplies those weights. Every encoder/decoder key is required.
    result = model.load_state_dict(state, strict=False)
    missing = [key for key in result.missing_keys if not key.startswith('clip_model.')]
    if missing or result.unexpected_keys:
        raise ValueError(f'Incompatible checkpoint: missing={missing}, unexpected={result.unexpected_keys}')
    clip_keys = [key for key in state if key.startswith('clip_model.')]
    if clip_keys and any(key.startswith('clip_model.') for key in result.missing_keys):
        raise ValueError('Checkpoint has an incomplete CLIP state')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    init = parser.add_mutually_exclusive_group(required=True)
    init.add_argument('--init-checkpoint', type=Path)
    init.add_argument('--resume', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch-size', type=int, default=20)
    parser.add_argument('--num-workers', type=int, default=16)
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--max-steps', type=int, default=0, help='Bounded smoke run; zero runs all epochs')
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.num_workers < 0 or args.lr <= 0 or args.max_steps < 0:
        parser.error('Invalid training limits')
    if args.output.exists():
        parser.error('--output must be a new directory')
    torch.manual_seed(args.seed)
    dataset = CaptionedMotions(args.data)
    checkpoint = args.resume or args.init_checkpoint
    payload = load_checkpoint(checkpoint)
    model = build_model(args.device, dataset.x.shape[-1])
    initialize(model, payload)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr)
    start_epoch, step = 0, 0
    dataset_hash = sha256(args.data)
    if args.resume:
        if not isinstance(payload, dict) or payload.get('format_version') != 1 or 'optimizer' not in payload:
            raise ValueError('Optimizer resume needs a fine-tuning checkpoint; use --init-checkpoint for legacy weights')
        if not payload.get('epoch_complete'):
            raise ValueError('A bounded partial-epoch checkpoint supports weight initialization only')
        if payload['dataset_sha256'] != dataset_hash:
            raise ValueError('Resume dataset differs from the saved training dataset')
        optimizer.load_state_dict(payload['optimizer'])
        start_epoch, step = payload['epoch'], payload['step']
        torch.set_rng_state(payload['rng_state'])
        if torch.cuda.is_available() and payload.get('cuda_rng_state') is not None:
            torch.cuda.set_rng_state_all(payload['cuda_rng_state'])
    del payload
    if start_epoch >= args.epochs:
        raise ValueError('--epochs must exceed the resumed completed epoch')
    iterator = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                          num_workers=args.num_workers, pin_memory=args.device.startswith('cuda'))
    reference = model.encoder.skelEmbedding.weight.detach().cpu().clone()
    frozen_clip = model.clip_model.token_embedding.weight.detach().cpu().clone()
    args.output.mkdir(parents=True)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    config.update(dataset_sha256=dataset_hash, initialized_from_sha256=sha256(checkpoint),
                  motion_shape=list(dataset.x.shape), clip_training='',
                  losses={'rc': 100, 'rcxyz': 100, 'vel': 100, 'text_cosine': 1})
    (args.output / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    stop = False
    with (args.output / 'losses.jsonl').open('w') as log:
        for epoch in range(start_epoch + 1, args.epochs + 1):
            model.train()
            model.clip_model.eval()
            for batch_index, batch in enumerate(iterator):
                batch = {key: value.to(args.device) if torch.is_tensor(value) else value
                         for key, value in batch.items()}
                optimizer.zero_grad(set_to_none=True)
                batch = model(batch)
                loss, losses = model.compute_loss(batch)
                if not torch.isfinite(loss):
                    raise FloatingPointError(f'Nonfinite loss at epoch {epoch}, batch {batch_index}')
                loss.backward()
                optimizer.step()
                step += 1
                entry = {'epoch': epoch, 'step': step, **losses}
                log.write(json.dumps(entry) + '\n')
                log.flush()
                print(json.dumps(entry), flush=True)
                stop = bool(args.max_steps and step >= args.max_steps)
                if stop:
                    break
            epoch_complete = batch_index + 1 == len(iterator)
            saved = {'format_version': 1, 'model': model.state_dict(),
                     'optimizer': optimizer.state_dict(), 'epoch': epoch, 'step': step,
                     'epoch_complete': epoch_complete, 'dataset_sha256': dataset_hash,
                     'rng_state': torch.get_rng_state(),
                     'cuda_rng_state': torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None}
            temporary = args.output / 'checkpoint.tmp'
            torch.save(saved, temporary)
            temporary.replace(args.output / 'checkpoint.pth.tar')
            if stop:
                break
    model.eval()
    sample = {key: value[None].to(args.device) for key, value in dataset[0].items() if torch.is_tensor(value)}
    with torch.no_grad():
        latent = model.encoder(sample)['mu']
    report = {'status': 'PASS', 'steps': step, 'epoch': epoch, 'epoch_complete': epoch_complete,
              'latent_shape': list(latent.shape), 'latent_finite': bool(torch.isfinite(latent).all()),
              'encoder_weight_max_change': float((model.encoder.skelEmbedding.weight.detach().cpu() - reference).abs().max()),
              'clip_unchanged': bool(torch.equal(model.clip_model.token_embedding.weight.detach().cpu(), frozen_clip)),
              'checkpoint_sha256': sha256(args.output / 'checkpoint.pth.tar')}
    if not report['latent_finite'] or not report['clip_unchanged'] or report['encoder_weight_max_change'] == 0:
        raise RuntimeError(f'Fine-tuning verification failed: {report}')
    (args.output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print('MOTION_ENCODER_FINETUNE_PASS ' + json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
