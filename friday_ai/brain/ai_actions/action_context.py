"""Context definitions for AI Actions."""

from __future__ import annotations
from dataclasses import dataclass, field
import time

from friday_ai.brain.ai_session import AISession
from friday_ai.brain.ai_actions.action_registry import AIAction


@dataclass
class ActionContext:
    """Localized context gathered specifically for this action invocation."""
    file_path: str = ""
    language: str = ""
    selected_text: str = ""
    cursor_line: int = -1
    surrounding_code: str = ""
    
    # Can carry additional specific payload later
    metadata: dict = field(default_factory=dict)


@dataclass
class AIActionRequest:
    """Encapsulates a full request to execute an AI Action."""
    request_id: str
    action: AIAction
    context: ActionContext
    session: AISession | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
