import gymnasium as gym

from . import agents, flat_env_cfg, diffusion_env_cfg

##
# Register Gym environments.
##

# G1 Diffusion Policy (Direct environment - for DiffuseCLOC evaluation)
gym.register(
    id="Isaac-PegasusMoDye-Diffusion-G1-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": diffusion_env_cfg.G1DiffusionEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPORunnerCfg",
    },
)

# G1 Data Collection (RL policy inference + privileged obs for data collection)
gym.register(
    id="Isaac-PegasusMoDye-DataCollection-G1-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": diffusion_env_cfg.G1DiffusionDataCollectionEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPOModNormRunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPORunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-PrivPrivObs-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatPrivPrivObsEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPORunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-PropPropObs-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatPropPropObsEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPORunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-NoisePrivObs-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatNoisePrivObsEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPORunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-ProjGravObs-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatProjGravObsEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPORunnerCfg",
    },
)
gym.register(
    id="Tracking-Flat-G1-ProjGravObs-MNMLP-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatProjGravObsEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPOModNormRunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-ProjGravObs-MNMLP-CollectData-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatProjGravObsEnvCfg_MotionEndReset,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPOModNormRunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-ProjGravObs-MNMLP-LargeHand-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatProjGravObsEnvCfg_LargeHand,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPOModNormRunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-ProjGravObs-MNMLP-LargeHandHeavy-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatProjGravObsEnvCfg_LargeHandHeavy,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPOModNormRunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-Wo-State-Estimation-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatWoStateEstimationEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatPPORunnerCfg",
    },
)

gym.register(
    id="Tracking-Flat-G1-Low-Freq-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point":
        flat_env_cfg.G1FlatLowFreqEnvCfg,
        "rsl_rl_cfg_entry_point":
        f"{agents.__name__}.rsl_rl_ppo_cfg:G1FlatLowFreqPPORunnerCfg",
    },
)
