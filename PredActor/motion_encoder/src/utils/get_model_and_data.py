from ..datasets.get_dataset import get_datasets
from ..models.get_model import get_model as get_gen_model
import clip
import torch
from omegaconf import OmegaConf
import os


def get_model_and_data(parameters, split="train"):

    # clip_model, preprocess = clip.load("ViT-B/32", device=device)  # Must set jit=False for training
    clip_model, clip_preprocess = clip.load("ViT-B/32", device=parameters['device'], jit=False)  # Must set jit=False for training
    if torch.device(parameters['device']).type == 'cuda':
        clip.model.convert_weights(clip_model)

    for domain in parameters.get('clip_training', '').split('_'):
        clip_num_layers = parameters.get('clip_layers', 12)
        if domain == 'text':
            if not parameters.get('init_checkpoint'):
                clip_model.initialize_parameters()
            clip_model.transformer.resblocks = clip_model.transformer.resblocks[:clip_num_layers]
        if domain == 'image':
            if not parameters.get('init_checkpoint'):
                clip_model.initialize_parameters()
            clip_model.visual.transformer = clip_model.transformer.resblocks[:clip_num_layers]

    # NO Clip Training ,Freeze CLIP weights
    if parameters.get('clip_training', '') == '':
        clip_model.eval()
        for p in clip_model.parameters():
            p.requires_grad = False

    datasets = get_datasets(parameters, clip_preprocess, split)
    model = get_gen_model(parameters, clip_model)
    if parameters.get('init_checkpoint'):
        initialize_training_checkpoint(model, parameters['init_checkpoint'])
    return model, datasets


def initialize_training_checkpoint(model, checkpoint_path):
    """Initialize model weights without discarding a checkpoint's learned text encoder."""
    payload = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    state = payload.get('model', payload)
    result = model.load_state_dict(state, strict=False)
    allowed_missing = not model.clip_training and not any(key.startswith('clip_model.') for key in state)
    missing = [key for key in result.missing_keys
               if not (allowed_missing and key.startswith('clip_model.'))]
    if missing or result.unexpected_keys:
        raise ValueError(f'Incompatible initialization checkpoint: missing={missing}, unexpected={result.unexpected_keys}')
    print(f'Initialized model and CLIP weights from {checkpoint_path}; optimizer starts fresh')


def get_motion_clip(config_path=None, checkpoint_path=None, device="cuda"):
    """
    Load MotionCLIP model with clean Hydra-based configuration.
    
    Args:
        config_path: Path to config YAML file. If None, uses default config.
        checkpoint_path: Path to model checkpoint file (.pth.tar). If None, returns untrained model.
        device: Device to load model on ('cuda' or 'cpu')
    
    Returns:
        model: MotionCLIP model
        cfg: Configuration object (OmegaConf)
    
    Example:
        # Load with default config
        model, cfg = get_motion_clip()
        
        # Load with custom config and checkpoint
        model, cfg = get_motion_clip(
            config_path='./exps/paper-model/opt.yaml',
            checkpoint_path='./exps/paper-model/checkpoint_0100.pth.tar'
        )
    """
    # Load configuration
    if config_path is None:
        # Use default config from src/config
        default_config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config', 'default_cfg.yaml'
        )
        cfg = OmegaConf.load(default_config_path)
    else:
        # Load custom config
        cfg = OmegaConf.load(config_path)
    
    # Set device
    if isinstance(device, int):
        device_str = f"cuda:{device}"
    else:
        device_str = device
    
    # Convert config to parameters dict for backward compatibility
    parameters = _config_to_parameters(cfg, device_str)
    
    # Load CLIP model
    clip_model_name = parameters.get('clip_model_name', 'ViT-B/32')
    clip_model, _ = clip.load(clip_model_name, device=device_str, jit=False)
    clip.model.convert_weights(clip_model)
    
    # Configure CLIP layers if specified
    clip_training = parameters.get('clip_training', '')
    clip_num_layers = parameters.get('clip_layers', 12)
    
    for domain in clip_training.split('_'):
        if domain == 'text':
            clip_model.initialize_parameters()
            clip_model.transformer.resblocks = clip_model.transformer.resblocks[:clip_num_layers]
        if domain == 'image':
            clip_model.initialize_parameters()
            clip_model.visual.transformer = clip_model.transformer.resblocks[:clip_num_layers]
    
    # Freeze CLIP if not training
    if clip_training == '':
        clip_model.eval()
        for p in clip_model.parameters():
            p.requires_grad = False
    
    # Create MotionCLIP model
    model = get_gen_model(parameters, clip_model)
    
    # Load checkpoint if provided
    if checkpoint_path is not None:
        print(f"Loading checkpoint from {checkpoint_path}")
        state_dict = torch.load(checkpoint_path, map_location=device_str)
        
        # Handle different checkpoint formats
        if 'model' in state_dict:
            model_state = state_dict['model']
        else:
            model_state = state_dict
        
        # Load weights without CLIP (CLIP is frozen)
        from ..utils.misc import load_model_wo_clip
        load_model_wo_clip(model, state_dict)
        print("Checkpoint loaded successfully")
    
    model.eval()
    return model, cfg


def _config_to_parameters(cfg, device):
    """Convert OmegaConf config to flat parameters dict for backward compatibility."""
    parameters = {}
    
    # Model parameters
    if 'model' in cfg:
        model_cfg = cfg.model
        pose_rep = model_cfg.get('pose_rep', 'rot6d')
        jointstype = model_cfg.get('jointstype', 'vertices')
        if cfg.model.get('use_g1'):
            njoints = 30
        else:
            # Compute njoints and nfeats based on pose representation
            # These are dataset-dependent but we use standard values
            if jointstype == 'vertices':
                njoints = 24  # SMPL vertices
            elif jointstype in ['a2m', 'a2mpl']:
                njoints = 18  # action2motion joints
            elif jointstype == 'smpl':
                njoints = 24  # SMPL joints
            elif jointstype == 'vibe':
                njoints = 21  # VIBE joints
            else:
                njoints = 24  # default
        
        # Add one joint for global rotation if glob=True
        glob = model_cfg.get('glob', True)
        translation = model_cfg.get('translation', True)
        if glob and not cfg.model.get('use_g1'):
            njoints += 1  # Add global rotation joint (e.g., 24 -> 25)
        if pose_rep != 'xyz' and translation:
            njoints += 1  # Add translation joint

        # Number of features per joint depends on pose representation
        if pose_rep == 'rot6d':
            nfeats = 6  # 6D rotation
        elif pose_rep == 'posquat':
            nfeats = 7  # position + quaternion
        elif pose_rep == 'posvel':
            nfeats = 6  # position + velocity
        elif pose_rep == 'rotmat':
            nfeats = 9  # 3x3 rotation matrix
        elif pose_rep == 'rotquat':
            nfeats = 4  # quaternion
        elif pose_rep == 'rotvec':
            nfeats = 3  # rotation vector
        elif pose_rep == 'xyz':
            nfeats = 3  # xyz coordinates
        else:
            nfeats = 6  # default to rot6d
        
        parameters.update({
            'archiname': model_cfg.get('archiname', 'transformer'),
            'modeltype': model_cfg.get('modeltype', 'cvae'),
            'activation': model_cfg.get('activation', 'gelu'),
            'latent_dim': model_cfg.get('latent_dim', 512),
            'num_layers': model_cfg.get('num_layers', 8),
            'num_frames': model_cfg.get('num_frames', 60),
            'num_heads': model_cfg.get('num_heads', 4),
            'ff_size': model_cfg.get('ff_size', 1024),
            'dropout': model_cfg.get('dropout', 0.1),
            'pose_rep': pose_rep,
            'jointstype': jointstype,
            'njoints': njoints,
            'nfeats': nfeats,
            'num_classes': 1,  # Not used in inference mode
            'glob': model_cfg.get('glob', True),
            'glob_rot': model_cfg.get('glob_rot', [3.141592653589793, 0, 0]),
            'translation': model_cfg.get('translation', True),
            'vertstrans': model_cfg.get('vertstrans', False),
            'align_pose_frontview': model_cfg.get('align_pose_frontview', False),
            'normalize_encoder_output': model_cfg.get('normalize_encoder_output', False),
            'outputxyz': model_cfg.get('outputxyz', True),
        })
        
        # Losses and lambdas
        if 'losses' in model_cfg:
            parameters['losses'] = list(model_cfg.losses)
        if 'lambdas' in model_cfg:
            parameters['lambdas'] = dict(model_cfg.lambdas)
    
    # CLIP parameters
    if 'clip' in cfg:
        clip_cfg = cfg.clip
        parameters.update({
            'clip_model_name': clip_cfg.get('model_name', 'ViT-B/32'),
            'clip_training': clip_cfg.get('training', ''),
            'clip_layers': clip_cfg.get('layers', 12),
            'clip_text_losses': list(clip_cfg.get('text_losses', ['cosine'])),
            'clip_image_losses': list(clip_cfg.get('image_losses', ['cosine'])),
            'clip_mappers_type': clip_cfg.get('mappers_type', 'no_mapper'),
            'clip_map_text': clip_cfg.get('map_text', False),
            'clip_map_images': clip_cfg.get('map_images', False),
        })
        
        if 'lambdas' in clip_cfg:
            parameters['clip_lambdas'] = OmegaConf.to_container(clip_cfg.lambdas, resolve=True)
    
    # Device
    parameters['device'] = device
    parameters['cuda'] = 'cuda' in device
    
    return parameters
