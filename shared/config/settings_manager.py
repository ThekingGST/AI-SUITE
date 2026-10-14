"""Settings Manager for runtime configurations (JSON based)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shared.config.path_manager import PathManager


class SettingsManager:
    """Manages application settings stored in AppData as JSON."""
    
    def __init__(self) -> None:
        self.settings_file = PathManager.get_appdata_dir() / "settings.json"
        self._cache: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load settings from JSON, creating default if missing."""
        if not self.settings_file.exists():
            self._save()
            return
            
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        except Exception:
            self._cache = {}

    def _save(self) -> None:
        """Save settings to JSON."""
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=4)

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._save()
