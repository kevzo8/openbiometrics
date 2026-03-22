from pathlib import Path

from openbiometrics_sdk.client import OpenBiometrics

# Single source of truth: /VERSION at repo root
_VERSION_FILE = Path(__file__).parent.parent.parent.parent / "VERSION"
__version__ = _VERSION_FILE.read_text().strip() if _VERSION_FILE.exists() else "0.0.0-dev"

__all__ = ["OpenBiometrics", "__version__"]
