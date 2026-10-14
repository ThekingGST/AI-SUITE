from dataclasses import dataclass
from typing import Any

@dataclass
class MemoryItem:
    content: str
    metadata: Any
    role: str = ""

class MemoryEngine:
    def __init__(self, eb, sp):
        self._store = []
        
    def search(self, scope, type, tags=None, assistant_id=None):
        results = []
        for item in self._store:
            if item.metadata.scope == scope and item.metadata.type == type:
                if tags:
                    if not all(t in item.metadata.tags for t in tags):
                        continue
                if assistant_id:
                    if item.metadata.assistant_id != assistant_id:
                        continue
                results.append(item)
        return results
        
    def update(self, item):
        pass
        
    def store(self, content, metadata, role=""):
        self._store.append(MemoryItem(content, metadata, role))
