import os

MOTIONCLIP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SMPL_DATA_PATH = os.path.join(MOTIONCLIP_ROOT, "models/smpl")
SMPL_KINTREE_PATH = os.path.join(SMPL_DATA_PATH, "kintree_table.pkl")
SMPL_MODEL_PATH = os.path.join(SMPL_DATA_PATH, "SMPL_NEUTRAL.pkl")
JOINT_REGRESSOR_TRAIN_EXTRA = os.path.join(SMPL_DATA_PATH, 'J_regressor_extra.npy')

SMPLH_AMASS_PATH = os.path.join(MOTIONCLIP_ROOT, "models/smplh")
SMPLH_AMASS_MODEL_PATH = os.path.join(SMPLH_AMASS_PATH, "neutral/model.npz")
SMPLH_AMASS_MALE_MODEL_PATH = os.path.join(SMPLH_AMASS_PATH, "male/model.npz")
SMPLH_AMASS_FEMALE_MODEL_PATH = os.path.join(SMPLH_AMASS_PATH, "female/model.npz")

SMPLX_DATA_PATH = os.path.join(MOTIONCLIP_ROOT, "models/smplx/")
SMPLX_MODEL_PATH = os.path.join(SMPLX_DATA_PATH, "SMPLX_NEUTRAL.pkl")
SMPLX_MALE_MODEL_PATH = os.path.join(SMPLX_DATA_PATH, "SMPLX_MALE.pkl")
SMPLX_FEMALE_MODEL_PATH = os.path.join(SMPLX_DATA_PATH, "SMPLX_FEMALE.pkl")

JOINT_REGRESSOR_TRAIN_EXTRA = os.path.join(SMPL_DATA_PATH, 'J_regressor_extra.npy')

JOINT_REGRESSOR_TRAIN_EXTRA = os.path.join(SMPL_DATA_PATH, 'J_regressor_extra.npy')

ROT_CONVENTION_TO_ROT_NUMBER = {
    'legacy': 23,
    'no_hands': 21,
    'full_hands': 51,
    'mitten_hands': 33,
    'g1_dof': 29,  # G1 robot DOF count (adjust based on actual G1 configuration)
}

GENDERS = ['neutral', 'male', 'female']
NUM_BETAS = 10

# G1 Robot Configuration
G1_NUM_DOFS = 29  # Total DOF count for G1 robot
G1_NUM_BODIES = 20  # Number of bodies/links in G1 robot (adjust based on actual)
G1_JOINT_NAMES = [
    'root', 'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw',
    'left_knee', 'left_ankle_pitch', 'left_ankle_roll',
    'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw',
    'right_knee', 'right_ankle_pitch', 'right_ankle_roll',
    'torso', 'left_shoulder_pitch', 'left_shoulder_roll', 'left_shoulder_yaw',
    'left_elbow', 'right_shoulder_pitch', 'right_shoulder_roll',
    'right_shoulder_yaw', 'right_elbow',
    # Add more based on actual G1 configuration
]
