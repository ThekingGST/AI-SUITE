from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from ai_suite.core.registry import ServiceContainer
from ai_suite.core.memory.engine import MemoryEngine
from ai_suite.core.memory.types import MemoryScope, MemoryType, MemoryMetadata
from jarvis_ai.config import MEMORY_DB
from jarvis_ai.utils.logger import LOGGER

class MemoryStore:
    """Thin adapter mapping legacy Jarvis memory onto the shared AI Suite MemoryEngine."""

    def __init__(self, db_path: Path = MEMORY_DB, assistant_id: str = "jarvis") -> None:
        self.db_path = db_path
        self.assistant_id = assistant_id
        # Temporary conversation history list (Pillar 1) so it doesn't pollute long-term SQLite
        self._conversation_history = []
        LOGGER.info(f"MemoryStore initialized for assistant: {assistant_id}")

    @property
    def _engine(self) -> MemoryEngine:
        return ServiceContainer.get(MemoryEngine)

    def remember(self, content: str, source: str = "user_chat") -> None:
        """Create an explicit persistent memory."""
        metadata = MemoryMetadata(
            scope=MemoryScope.ASSISTANT,
            type=MemoryType.PREFERENCE,
            source=source,
            assistant_id=self.assistant_id,
            tags=[]
        )
        res = self._engine.store(content=content, metadata=metadata)
        if res:
            LOGGER.info("Memory saved: %s", content)
        else:
            LOGGER.warning("Memory rejected: %s", content)

    def search_memories(self, query: str, limit: int = 5) -> List[str]:
        """Search active relevant memories."""
        results = self._engine.search(query=query, assistant_id=self.assistant_id, limit=limit)
        return [r.content for r in results]
        
    def list_memories(self) -> List[str]:
        """Get all active memories for transparency."""
        results = self._engine.get_all(assistant_id=self.assistant_id)
        return [r.content for r in results]

    def forget(self, query: str) -> bool:
        """Find relevant memories matching the exact intent and deactivate them all."""
        results = self._engine.search(query=query, assistant_id=self.assistant_id, limit=50, operator="AND")
        if results:
            for r in results:
                self._engine.deactivate(r.id)
                LOGGER.info("Memory deactivated: %s", r.content)
            return True
        return False

    def add_message(self, role: str, content: str) -> None:
        """Conversation history is strictly ephemeral now (Pillar 1)."""
        self._conversation_history.append({"role": role, "content": content})

    def recent_messages(self, limit: int = 16) -> list[dict[str, str]]:
        return self._conversation_history[-limit:]

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        # We can drop this or log it to a separate table/file, but to avoid 
        # database bloat with ephemeral logs, we just log to standard logger.
        LOGGER.debug(f"[OBSERVATION] {event_type}: {payload}")
