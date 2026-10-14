"""Workspace persistence service.

Saves and restores application state to/from a JSON file so that FRIDAY
remembers the user's layout, recent projects, and open tabs between sessions.

Storage location: ``friday_ai/data/workspace.json``

This is pure I/O logic — no UI knowledge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from friday_ai.core.config import DATA_DIR
from shared.logger import get_logger

LOG = get_logger("friday.persistence")

_WORKSPACE_FILE = DATA_DIR / "workspace.json"


def _default_state() -> dict[str, Any]:
    """Return the default workspace state."""
    return {
        "recent_projects": [],
        "last_project": None,
        "window": {
            "x": -1,
            "y": -1,
            "width": 1440,
            "height": 900,
            "maximized": False,
        },
        "layout": {
            "h_splitter": [],
            "v_splitter": [],
        },
    }


class WorkspacePersistence:
    """JSON-backed workspace state persistence.

    Usage::

        ws = WorkspacePersistence()
        ws.load()
        ws.set("last_project", "/path/to/project")
        ws.save()
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = _default_state()

    # ── Load / Save ──────────────────────────────────────────────────────

    def load(self) -> None:
        """Load state from disk.  Uses defaults if the file is missing."""
        if not _WORKSPACE_FILE.exists():
            LOG.info("No workspace file found, using defaults")
            return

        try:
            raw = _WORKSPACE_FILE.read_text(encoding="utf-8")
            loaded = json.loads(raw)
            # Merge with defaults so new keys are always present.
            defaults = _default_state()
            for key in defaults:
                if key not in loaded:
                    loaded[key] = defaults[key]
                elif isinstance(defaults[key], dict):
                    merged = {**defaults[key], **loaded.get(key, {})}
                    loaded[key] = merged
            self._data = loaded
            LOG.info("Workspace state loaded from %s", _WORKSPACE_FILE)
        except (json.JSONDecodeError, OSError) as exc:
            LOG.warning("Failed to load workspace state: %s", exc)
            self._data = _default_state()

    def save(self) -> None:
        """Persist current state to disk."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            _WORKSPACE_FILE.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            LOG.debug("Workspace state saved")
        except OSError as exc:
            LOG.warning("Failed to save workspace state: %s", exc)

    # ── Accessors ────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """Get a top-level value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a top-level value."""
        self._data[key] = value

    # ── Convenience properties ───────────────────────────────────────────

    @property
    def recent_projects(self) -> list[str]:
        return self._data.get("recent_projects", [])

    @recent_projects.setter
    def recent_projects(self, value: list[str]) -> None:
        self._data["recent_projects"] = value

    @property
    def last_project(self) -> str | None:
        return self._data.get("last_project")

    @last_project.setter
    def last_project(self, value: str | None) -> None:
        self._data["last_project"] = value

    @property
    def window_state(self) -> dict[str, Any]:
        return self._data.get("window", {})

    @window_state.setter
    def window_state(self, value: dict[str, Any]) -> None:
        self._data["window"] = value

    @property
    def layout_state(self) -> dict[str, Any]:
        return self._data.get("layout", {})

    @layout_state.setter
    def layout_state(self, value: dict[str, Any]) -> None:
        self._data["layout"] = value
