from typing import Optional, Any
from jarvis_ai.utils.logger import LOGGER

class ProjectManager:
    """Manages active project state for workspaces."""
    
    def __init__(self, event_bus: Any):
        self.event_bus = event_bus
        self.active_project_path: Optional[str] = None
        
    def open_project(self, path: str) -> None:
        """Sets the global active project and notifies workspaces."""
        if self.active_project_path == path:
            return
            
        LOGGER.info(f"Opening project: {path}")
        self.active_project_path = path
        
        if hasattr(self.event_bus, "projectOpened"):
            self.event_bus.projectOpened.emit(path)
            
    def close_project(self) -> None:
        """Closes the current project."""
        if not self.active_project_path:
            return
            
        LOGGER.info(f"Closing project: {self.active_project_path}")
        self.active_project_path = None
        
        if hasattr(self.event_bus, "projectClosed"):
            self.event_bus.projectClosed.emit()