from __future__ import annotations

import sys
from shared.config.path_manager import PathManager

CURRENT_DIR = PathManager.get_bundle_dir() / "jarvis_ai"
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Import onnxruntime BEFORE tensorflow/deepface to prevent DLL conflicts on
# Windows.  TensorFlow can pollute the DLL search path with incompatible
# shared libraries, causing onnxruntime_pybind11_state to fail to load.
try:
    import onnxruntime  # noqa: F401
except ImportError:
    pass

from jarvis_ai.config import ensure_directories, path_diagnostics
from jarvis_ai.ui.main_window import run_app
from jarvis_ai.utils.logger import LOGGER


def main() -> int:
    ensure_directories()
    LOGGER.info("Starting JARVIS.")
    for name, value in path_diagnostics().items():
        LOGGER.info("PATH %s=%s", name, value)
        
    from ai_suite.core.events import EventBus
    from ai_suite.core.registry import ServiceContainer
    from ai_suite.core.memory.engine import MemoryEngine
    from ai_suite.core.memory.storage import SQLiteStorageProvider
    from shared.config.config_manager import ConfigManager
    
    if ServiceContainer.get(MemoryEngine) is None:
        event_bus = EventBus()
        storage_provider = SQLiteStorageProvider(db_path=ConfigManager.MEMORY_DB)
        memory_engine = MemoryEngine(event_bus, storage_provider)
        ServiceContainer.register(MemoryEngine, memory_engine)
        
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
