"""Change Set: Structured models for AI code modifications."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
import time


class ChangeType(Enum):
    REPLACE = auto()
    INSERT = auto()
    DELETE = auto()


class EditStatus(Enum):
    PENDING = auto()
    APPLIED = auto()
    REJECTED = auto()
    FAILED = auto()


@dataclass
class EditOperation:
    """A discrete structural modification to a text document."""
    original_text: str
    replacement_text: str
    change_type: ChangeType
    status: EditStatus = EditStatus.PENDING


@dataclass
class ChangeSet:
    """A collection of edit operations proposed for a specific file."""
    id: str
    file_path: str
    language: str
    summary: str
    operations: list[EditOperation]
    created_at: float = field(default_factory=time.time)
    source_action: str = ""
    provider: str = ""
    model: str = ""
