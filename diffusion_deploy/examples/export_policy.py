"""export_policy.py — back-compat shim (DEPLOY-WORKFLOW-GUI-017).

The canonical implementation now lives at
``diffusion_deploy/tools/export_policy.py``.  This module re-exports the
public API so existing invocations of ``python examples/export_policy.py ...``
keep working unchanged.
"""

import sys
import pathlib

# Same sys.path bootstrap as tools/export_policy.py so `diffusion_deploy.*`
# resolves when this shim is run directly.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from diffusion_deploy.tools.export_policy import (  # noqa: E402,F401
    _default_urdf_path,
    _derive_deploy_args,
    _load_export_config,
    main,
)

if __name__ == "__main__":
    main()
