"""Memory and conversation history for the AI."""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import deque

from friday_ai.core.signals import signals
from shared.logger import get_logger

LOG = get_logger("friday.memory")


@dataclass
class ChatMessage:
    role: str
    content: str


class ConversationMemory:
    """Manages chat history for the active project."""

    def __init__(self, max_history: int = 20) -> None:
        self.max_history = max_history
        self._history: deque[ChatMessage] = deque(maxlen=max_history)
        self._project_path: Path | None = None

        signals.project_opened.connect(self._on_project_opened)
        signals.project_closed.connect(self._on_project_closed)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to history and auto-save."""
        self._history.append(ChatMessage(role, content))
        self._save()

    def get_messages(self) -> list[dict[str, str]]:
        """Get history as API-compatible dicts."""
        return [asdict(m) for m in self._history]

    def clear(self) -> None:
        """Clear the current conversation."""
        self._history.clear()
        self._save()

    def _on_project_opened(self, path: str) -> None:
        self._project_path = Path(path)
        self._load()

    def _on_project_closed(self) -> None:
        self._project_path = None
        self._history.clear()

    @property
    def _save_file(self) -> Path | None:
        if not self._project_path:
            return None
        from friday_ai.services.project_manager import ProjectManager
        pdir = ProjectManager().get_project_data_dir(self._project_path)
        return pdir / "chat_history.json"

    def _save(self) -> None:
        if not self._save_file:
            return
        try:
            with open(self._save_file, "w", encoding="utf-8") as f:
                json.dump([asdict(m) for m in self._history], f, indent=2)
        except Exception as e:
            LOG.error("Failed to save chat history: %s", e)

    def _load(self) -> None:
        self._history.clear()
        if not self._save_file or not self._save_file.exists():
            return
        try:
            with open(self._save_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self._history.append(ChatMessage(**item))
        except Exception as e:
            LOG.error("Failed to load chat history: %s", e)
