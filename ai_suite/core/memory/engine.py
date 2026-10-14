import uuid
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, List, Optional
import re

from ai_suite.core.memory.types import MemoryScope, MemoryType, MemoryMetadata

LOGGER = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    id: str
    content: str
    metadata: MemoryMetadata
    role: str = ""
    created_at: str = ""
    updated_at: str = ""
    active: bool = True

class MemoryEngine:
    def __init__(self, eb, sp):
        self.eb = eb
        self.sp = sp
        
    def _is_secret(self, content: str) -> bool:
        """Reject obvious secrets from being stored as memory."""
        patterns = [
            r"sk-[a-zA-Z0-9]{32,}",  # Standard API key format
            r"Bearer\s+[A-Za-z0-9\-\._~+]+",  # Bearer tokens
            r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+",  # Password assignments
            r"(?i)api[_-]?key\s*[:=]\s*\S+",  # API key assignments
            r"(?i)access[_-]?token\s*[:=]\s*\S+" # Access tokens
        ]
        for p in patterns:
            if re.search(p, content):
                return True
        return False

    def store(self, content: str, metadata: MemoryMetadata, role: str = "") -> Optional[MemoryItem]:
        if self._is_secret(content):
            LOGGER.warning("Refused to store potential secret in memory.")
            return None
            
        mem_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        meta_json = json.dumps({"tags": metadata.tags, "role": role})
        
        try:
            self.sp.store(
                mem_id=mem_id,
                content=content,
                category=metadata.type.value,
                scope=metadata.scope.value,
                assistant_id=metadata.assistant_id,
                source=metadata.source,
                confidence=1.0,
                created_at=now,
                updated_at=now,
                active=1,
                metadata=meta_json
            )
            return MemoryItem(mem_id, content, metadata, role, now, now, True)
        except Exception as e:
            LOGGER.error("Failed to store memory: %s", e)
            return None

    def search(self, query: str, scope: str = None, assistant_id: str = None, limit: int = 5, operator: str = "OR") -> List[MemoryItem]:
        """Search via FTS5."""
        try:
            # Strip punctuation for safe FTS5 BM25 search
            clean_query = re.sub(r'[^\w\s]', '', query)
            terms = [term for term in clean_query.split() if len(term) > 2]
            if not terms:
                return []
            fts_query = f" {operator} ".join(terms)
            
            LOGGER.debug("Executing FTS5 Search: '%s'", fts_query)
            rows = self.sp.search_fts(fts_query, scope=scope, assistant_id=assistant_id, limit=limit)
            return [self._row_to_item(r) for r in rows]
        except Exception as e:
            LOGGER.error("Failed to search memory: %s", e)
            return []

    def get_all(self, scope: str = None, assistant_id: str = None) -> List[MemoryItem]:
        try:
            rows = self.sp.get_all_active(scope=scope, assistant_id=assistant_id)
            return [self._row_to_item(r) for r in rows]
        except Exception as e:
            LOGGER.error("Failed to get all memories: %s", e)
            return []

    def deactivate(self, mem_id: str):
        try:
            now = datetime.now(timezone.utc).isoformat()
            self.sp.deactivate(mem_id, now)
        except Exception as e:
            LOGGER.error("Failed to deactivate memory %s: %s", mem_id, e)

    def _row_to_item(self, row) -> MemoryItem:
        meta_dict = json.loads(row["metadata"]) if row["metadata"] else {}
        metadata = MemoryMetadata(
            scope=MemoryScope(row["scope"]),
            type=MemoryType(row["category"]),
            source=row["source"],
            assistant_id=row["assistant_id"],
            tags=meta_dict.get("tags", [])
        )
        return MemoryItem(
            id=row["id"],
            content=row["content"],
            metadata=metadata,
            role=meta_dict.get("role", ""),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            active=bool(row["active"])
        )
