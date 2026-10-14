"""Path Manager for resolving safe, deployment-aware paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from shared.config.deployment import detect_deployment_mode, DeploymentMode


class PathManager:
    """Centralizes path resolution to support PyInstaller _MEIPASS and AppData migration."""
    
    @staticmethod
    def get_bundle_dir() -> Path:
        """Get the base directory where static assets (icons, styles) are located.
        In PyInstaller, this is sys._MEIPASS. In dev, it's the project root.
        """
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parents[2]

    @staticmethod
    def get_executable_dir() -> Path:
        """Get the directory containing the executable (or entrypoint script)."""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        # In dev, the entrypoint is usually ai_suite/main.py or jarvis_ai/main.py,
        # but we treat the project root as the executable dir.
        return PathManager.get_bundle_dir()

    @staticmethod
    def get_appdata_dir() -> Path:
        """Get the writable directory for logs, cache, memory, settings.
        
        - Packaged/Dev: %LOCALAPPDATA%/AISuite
        - Portable: <executable_dir>/AISuiteData
        """
        mode = detect_deployment_mode()
        
        if mode == DeploymentMode.PORTABLE:
            data_dir = PathManager.get_executable_dir() / "AISuiteData"
        else:
            # Fallback to %LOCALAPPDATA% on Windows, ~/.local/share on Linux/Mac
            if os.name == "nt":
                local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
                data_dir = Path(local_appdata) / "AISuite"
            else:
                data_dir = Path(os.path.expanduser("~/.local/share/AISuite"))
                
        # Ensure it exists
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    @staticmethod
    def ensure_dir(path: Path) -> Path:
        """Ensure a directory exists and return it."""
        path.mkdir(parents=True, exist_ok=True)
        return path
