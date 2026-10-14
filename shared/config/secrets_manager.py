"""Secrets Manager for API keys and sensitive configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from shared.config.deployment import detect_deployment_mode, DeploymentMode
from shared.config.path_manager import PathManager


class SecretsManager:
    """Manages sensitive keys securely across deployment modes."""
    
    def __init__(self) -> None:
        self.mode = detect_deployment_mode()
        self.secrets_file = PathManager.get_appdata_dir() / "secrets.json"
        
        # In all modes, we still respect existing OS environment variables
        # In DEV mode, we load the .env file from the project root.
        if self.mode == DeploymentMode.DEVELOPMENT:
            env_file = PathManager.get_bundle_dir() / ".env"
            if env_file.exists():
                load_dotenv(env_file, override=False)
                
        # Load from secrets.json if it exists (Packaged/Portable mode overriding)
        self._cache: dict[str, str] = {}
        if self.secrets_file.exists():
            try:
                with open(self.secrets_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                pass

    def get_secret(self, key: str, default: str | None = None) -> str | None:
        """Get a secret, prioritizing secrets.json over os.environ."""
        if key in self._cache:
            return self._cache[key]
        return os.environ.get(key, default)

    def set_secret(self, key: str, value: str) -> None:
        """Store a secret securely in AppData."""
        self._cache[key] = value
        with open(self.secrets_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=4)
