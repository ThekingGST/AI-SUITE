from typing import Optional
from PyQt5.QtWidgets import QStackedWidget
from ai_suite.core.workspace.registry import WorkspaceRegistry
from jarvis_ai.utils.logger import LOGGER

class WorkspaceCoordinator:
    """Orchestrates workspace lifecycles, lazy loading, and UI switching."""
    
    def __init__(self, event_bus, registry: WorkspaceRegistry):
        self.event_bus = event_bus
        self.registry = registry
        self.stacked_widget: Optional[QStackedWidget] = None
        self.active_workspace_id: Optional[str] = None
        self._workspace_widgets = {} # workspace_id -> index in stacked widget
        
    def set_container(self, stacked_widget: QStackedWidget) -> None:
        """Binds the coordinator to the main UI container."""
        self.stacked_widget = stacked_widget
        
        # Pre-populate the container with workspaces, but do not initialize them yet (lazy load)
        for workspace in self.registry.get_all_workspaces():
            widget = workspace.get_widget()
            index = self.stacked_widget.addWidget(widget)
            self._workspace_widgets[workspace.id] = index
            LOGGER.info(f"Registered UI container for {workspace.id} at index {index}")

    def activate_workspace(self, workspace_id: str) -> None:
        """Safely switches to the requested workspace."""
        if self.stacked_widget is None:
            LOGGER.error("WorkspaceCoordinator has no UI container set!")
            return
            
        if workspace_id not in self._workspace_widgets:
            LOGGER.error(f"Cannot activate unknown workspace: {workspace_id}")
            return
            
        if self.active_workspace_id == workspace_id:
            return # Already active
            
        target = self.registry.get_workspace(workspace_id)
        
        # Suspend current
        if self.active_workspace_id:
            current = self.registry.get_workspace(self.active_workspace_id)
            if current:
                current.suspend()
                current.deactivate()
                
        # Activate target (this triggers initialize() if lazy loading)
        target.resume()
        
        # Switch UI
        self.stacked_widget.setCurrentIndex(self._workspace_widgets[workspace_id])
        
        # Emit cross-assistant event
        if self.active_workspace_id:
            self.event_bus.workspaceChanged.emit(self.active_workspace_id, workspace_id)
            
        self.active_workspace_id = workspace_id
        
    def request_cross_workspace_action(self, source_id: str, target_id: str, action: str, payload: dict) -> None:
        """Foundation for cross-workspace routing."""
        LOGGER.info(f"Cross-workspace request from {source_id} to {target_id}: {action}")
        # In the future, this will look up the target and execute the action if permitted
        
    def shutdown_all(self) -> None:
        """Clean shutdown of all workspaces."""
        for workspace in self.registry.get_all_workspaces():
            workspace.shutdown()