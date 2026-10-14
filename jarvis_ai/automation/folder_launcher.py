from __future__ import annotations

import os
from pathlib import Path

from jarvis_ai.utils.helpers import safe_open_path
from jarvis_ai.utils.logger import LOGGER


class FolderLauncher:
    """Safe launcher for known Windows user folders."""

    def __init__(self) -> None:
        home = Path.home()
        self.folders = {
            "desktop": home / "Desktop",
            "downloads": home / "Downloads",
            "download": home / "Downloads",
            "documents": home / "Documents",
            "document": home / "Documents",
            "pictures": home / "Pictures",
            "photos": home / "Pictures",
            "videos": home / "Videos",
            "music": home / "Music",
            "home": home,
        }

    def open_folder(self, name: str) -> str | None:
        key = name.strip().lower()
        path = self.folders.get(key)
        if path is None:
            return None
        if not path.exists() or not path.is_dir():
            LOGGER.warning("Folder not found: %s", path)
            return f"{name.title()} folder was not found."
        if safe_open_path(path):
            LOGGER.info("Opened folder: %s", path)
            return f"Opening {name}."
        LOGGER.warning("Failed to open folder: %s", path)
        return f"I could not open {name}."


def open_path_if_safe(path: Path) -> bool:
    if path.exists():
        return safe_open_path(path)
    return False
