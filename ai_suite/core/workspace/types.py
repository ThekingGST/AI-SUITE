from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

class NotificationPriority(str, Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SYSTEM = "SYSTEM"

class NotificationDestination(str, Enum):
    TOAST = "TOAST"
    SIDEBAR = "SIDEBAR"
    STATUS_BAR = "STATUS_BAR"
    VOICE = "VOICE"
    LOG = "LOG"

@dataclass
class WorkspaceContext:
    """Lightweight context providing scoped access to shared services."""
    workspace_id: str
    active_project_path: Optional[str] = None
    
@dataclass
class WorkspaceManifest:
    """Metadata for registering a workspace."""
    id: str
    name: str
    version: str
    icon: str
    capabilities: List[str]
    startup_priority: int = 100

@dataclass
class WorkspaceSession:
    """Persistent state of a workspace."""
    active_project: Optional[str] = None
    open_tabs: List[str] = field(default_factory=list)
    layout_state: Dict[str, Any] = field(default_factory=dict)
    navigation_history: List[str] = field(default_factory=list)
