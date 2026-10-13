import os

# Conveniences to other module directories via relative paths
ASSET_DIR = os.environ.get("PREDACTOR_ASSET_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../assets")))
