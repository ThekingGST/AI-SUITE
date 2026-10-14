from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

class DelegationTransparency(str, Enum):
    SILENT = "SILENT"
    INFORMATIONAL = "INFORMATIONAL"
    INTERACTIVE = "INTERACTIVE"

class AssistantState(str, Enum):
    UNLOADED = "UNLOADED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    BUSY = "BUSY"
    WAITING = "WAITING"
    DELEGATING = "DELEGATING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"

@dataclass
class ReasoningPolicy:
    """Configures how an assistant interfaces with the ModelManager."""
    reasoning_type: str  # e.g., "conversational", "structured_code", "research"
    fallback_allowed: bool = True
    context_window_limit: int = 8192
    
@dataclass
class AssistantProfile:
    """The identity and capabilities of an independent AI Assistant."""
    id: str
    display_name: str
    description: str
    workspace_id: str
    system_prompt: str
    reasoning_policy: ReasoningPolicy
    default_capabilities: List[str] = field(default_factory=list)
    supported_capabilities: List[str] = field(default_factory=list)
    routing_keywords: List[str] = field(default_factory=list)
    routing_priority: int = 50
    permissions: List[str] = field(default_factory=list)
    visibility: DelegationTransparency = DelegationTransparency.SILENT
    icon: str = "robot"
    theme: str = "default"

@dataclass
class DelegationContext:
    """The structured context transferred between assistants without duplicating memory."""
    task: str
    goal: str
    constraints: List[str]
    workspace_id: str
    source_assistant_id: str
    target_assistant_id: str
    project_path: Optional[str]
    relevant_memory_ids: List[str]
    relevant_files: List[str]
    user_intent: str

@dataclass
class DelegationRequest:
    id: str
    context: DelegationContext
    transparency: DelegationTransparency
    
@dataclass
class DelegationResponse:
    request_id: str
    status: str  # "SUCCESS", "FAILED"
    result: Any
    error_message: Optional[str] = None
