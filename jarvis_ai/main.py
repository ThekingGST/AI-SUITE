from __future__ import annotations

import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Import onnxruntime BEFORE tensorflow/deepface to prevent DLL conflicts on
# Windows.  TensorFlow can pollute the DLL search path with incompatible
# shared libraries, causing onnxruntime_pybind11_state to fail to load.
try:
    import onnxruntime  # noqa: F401
except ImportError:
    pass

from config import ensure_directories, path_diagnostics
from ui.main_window import run_app
from utils.logger import LOGGER


def main() -> int:
    ensure_directories()
    LOGGER.info("Starting JARVIS.")
    for name, value in path_diagnostics().items():
        LOGGER.info("PATH %s=%s", name, value)
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
