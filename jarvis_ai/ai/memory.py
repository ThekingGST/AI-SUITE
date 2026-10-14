
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_suite.core.registry import ServiceContainer
from ai_suite.core.memory.engine import MemoryEngine
from ai_suite.core.memory.types import MemoryScope, MemoryType, MemoryMetadata
from jarvis_ai.config import MEMORY_DB
from jarvis_ai.utils.logger import LOGGER

class MemoryStore:
    """Thin adapter mapping legacy Jarvis memory onto the shared AI Suite MemoryEngine."""

    def __init__(self, db_path: Path = MEMORY_DB) -> None:
        self.db_path = db_path
        LOGGER.info("Legacy MemoryStore initialized as adapter.")

    @property
    def _engine(self) -> MemoryEngine:
        return ServiceContainer.get(MemoryEngine)

    def remember(self, key: str, value: Any) -> None:
        normalized_key = key.strip().lower()
        payload = json.dumps(value, ensure_ascii=False)
        
        metadata = MemoryMetadata(
            scope=MemoryScope.GLOBAL,
            type=MemoryType.PREFERENCE,
            source="user_chat",
            tags=[f"key:{normalized_key}"]
        )
        
        # We need to simulate 'upsert'. Find existing and update, or store new.
        existing = self._engine.search(scope=MemoryScope.GLOBAL, type=MemoryType.PREFERENCE, tags=[f"key:{normalized_key}"])
        if existing:
            item = existing[0]
            item.content = payload
            self._engine.update(item)
        else:
            self._engine.store(content=payload, metadata=metadata)
            
        LOGGER.info("Memory saved via adapter: %s", normalized_key)

    def recall(self, key: str) -> Any | None:
        normalized_key = key.strip().lower()
        items = self._engine.search(scope=MemoryScope.GLOBAL, type=MemoryType.PREFERENCE, tags=[f"key:{normalized_key}"])
        if not items:
            return None
            
        try:
            return json.loads(items[0].content)
        except json.JSONDecodeError:
            return items[0].content

    def search_preferences(self, query: str) -> list[tuple[str, Any]]:
        # This is a bit tricky to map perfectly to exact string match.
        # We'll just return all preferences and filter in python.
        items = self._engine.search(scope=MemoryScope.GLOBAL, type=MemoryType.PREFERENCE)
        result = []
        like = query.strip().lower()
        
        for item in items:
            tag_key = next((t.split("key:")[1] for t in item.metadata.tags if t.startswith("key:")), None)
            if tag_key and like in tag_key:
                try:
                    val = json.loads(item.content)
                except json.JSONDecodeError:
                    val = item.content
                result.append((tag_key, val))
                
        return result

    def add_message(self, role: str, content: str) -> None:
        metadata = MemoryMetadata(
            scope=MemoryScope.SESSION,
            type=MemoryType.CONVERSATION,
            source="user_chat",
            assistant_id="jarvis"
        )
        self._engine.store(content=content, metadata=metadata, role=role)

    def recent_messages(self, limit: int = 16) -> list[dict[str, str]]:
        # MemoryEngine search returns oldest first because of created_at ASC
        # but retriever logic gives us standard chronologically sorted items
        items = self._engine.search(scope=MemoryScope.SESSION, type=MemoryType.CONVERSATION, assistant_id="jarvis")
        # Legacy expected oldest first historically, actually no, the caller reverses it! 
        # Wait, legacy returns chronologically oldest first up to limit.
        recent = items[-limit:]
        return [{"role": item.role, "content": item.content} for item in recent if item.role]

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        metadata = MemoryMetadata(
            scope=MemoryScope.GLOBAL,
            type=MemoryType.OBSERVATION,
            source="system_event",
            tags=[f"event:{event_type}"]
        )
        self._engine.store(content=json.dumps(payload, ensure_ascii=False), metadata=metadata)
