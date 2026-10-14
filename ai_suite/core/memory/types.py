from enum import Enum
from dataclasses import dataclass, field

class MemoryScope(Enum):
    GLOBAL = "global"
    SESSION = "session"
    PROJECT = "project"
    ASSISTANT = "assistant"
    TEMPORARY = "temporary"

class MemoryType(Enum):
    PREFERENCE = "preference"
    CONVERSATION = "conversation"
    OBSERVATION = "observation"
    FACT = "fact"
    PROJECT = "project"
    COMMAND = "command"
    SYSTEM = "system"
    KNOWLEDGE = "knowledge"

@dataclass
class MemoryMetadata:
    scope: MemoryScope
    type: MemoryType
    source: str
    assistant_id: str = "system"
    tags: list[str] = field(default_factory=list)
