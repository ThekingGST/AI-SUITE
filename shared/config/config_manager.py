"""Central Configuration Manager for AI Suite."""

from __future__ import annotations

from pathlib import Path

from shared.config.deployment import detect_deployment_mode, DeploymentMode
from shared.config.path_manager import PathManager
from shared.config.resource_manager import ResourceManager
from shared.config.secrets_manager import SecretsManager
from shared.config.settings_manager import SettingsManager


class _ConfigManager:
    """Singleton facade for application configuration."""

    def __init__(self) -> None:
        self.mode: DeploymentMode = detect_deployment_mode()
        self.paths = PathManager
        self.resources = ResourceManager
        self.settings = SettingsManager()
        self.secrets = SecretsManager()

    # Convenience accessors to emulate legacy jarvis_ai/config.py constants
    
    @property
    def BASE_DIR(self) -> Path:
        return self.paths.get_bundle_dir() / "jarvis_ai"

    @property
    def PROJECT_ROOT(self) -> Path:
        return self.paths.get_bundle_dir()

    @property
    def FRIDAY_ROOT(self) -> Path:
        return self.paths.get_bundle_dir() / "friday_ai"

    @property
    def ASSETS_DIR(self) -> Path:
        return self.resources.get_assets_dir()

    @property
    def ICONS_DIR(self) -> Path:
        return self.resources.get_icons_dir()

    @property
    def MODELS_DIR(self) -> Path:
        return self.resources.get_models_dir()

    @property
    def DATA_DIR(self) -> Path:
        return self.resources.get_data_dir()

    @property
    def LOG_DIR(self) -> Path:
        return self.resources.get_log_dir()

    @property
    def FRIDAY_DATA_DIR(self) -> Path:
        return self.paths.ensure_dir(self.DATA_DIR / "friday")

    @property
    def INTRUDER_DIR(self) -> Path:
        return self.paths.ensure_dir(self.DATA_DIR / "intruders")

    @property
    def CAPTURES_DIR(self) -> Path:
        return self.paths.ensure_dir(self.DATA_DIR / "captures")

    @property
    def SCREENSHOT_DIR(self) -> Path:
        return self.paths.ensure_dir(self.DATA_DIR / "screenshots")

    @property
    def FACE_DATASET_DIR(self) -> Path:
        return self.paths.ensure_dir(self.DATA_DIR / "faces")

    @property
    def OBJECT_DATASET_DIR(self) -> Path:
        return self.paths.ensure_dir(self.DATA_DIR / "objects")

    @property
    def FACE_EMBEDDINGS_DB(self) -> Path:
        return self.DATA_DIR / "face_embeddings.pkl"

    @property
    def MEMORY_DB(self) -> Path:
        return self.DATA_DIR / "jarvis_memory.sqlite3"

    @property
    def OWNER_EMBEDDINGS(self) -> Path:
        return self.DATA_DIR / "owner_embeddings.json"


# Export the singleton
ConfigManager = _ConfigManager()
