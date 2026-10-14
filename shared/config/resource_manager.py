"""Resource Manager for resolving specific application assets and models."""

from __future__ import annotations

from pathlib import Path
from shared.config.path_manager import PathManager


class ResourceManager:
    """Provides centralized access to application resources (bundled and external)."""

    @staticmethod
    def get_assets_dir() -> Path:
        """Get the directory containing bundled assets (icons, styles, logos)."""
        return PathManager.get_bundle_dir() / "assets"

    @staticmethod
    def get_icons_dir() -> Path:
        """Get the directory containing application icons."""
        return ResourceManager.get_assets_dir() / "icons"

    @staticmethod
    def get_models_dir() -> Path:
        """Get the directory containing AI models.
        
        Models are massive and should NOT be bundled inside PyInstaller's _MEIPASS.
        They must remain adjacent to the executable in packaged mode, or in the
        project root in development mode.
        """
        # In portable/packaged mode, expect models next to the exe
        return PathManager.get_executable_dir() / "models"

    @staticmethod
    def get_data_dir() -> Path:
        """Get the base directory for runtime writable data (e.g. captures, embeddings)."""
        return PathManager.get_appdata_dir()

    @staticmethod
    def get_log_dir() -> Path:
        """Get the directory for rotating logs."""
        return PathManager.ensure_dir(PathManager.get_appdata_dir() / "logs")

    @staticmethod
    def get_cache_dir() -> Path:
        """Get the directory for temporary runtime caches."""
        return PathManager.ensure_dir(PathManager.get_appdata_dir() / "cache")
