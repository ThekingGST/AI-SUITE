from typing import Dict, List, Optional
from ai_suite.core.workspace.base import BaseWorkspace
from jarvis_ai.utils.logger import LOGGER

class WorkspaceRegistry:
    """Maintains metadata and instances of all available workspaces."""
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._workspaces: Dict[str, BaseWorkspace] = {}

    def register(self, workspace: BaseWorkspace) -> None:
        if workspace.id in self._workspaces:
            LOGGER.warning(f"Workspace {workspace.id} is already registered.")
            return
            
        self._workspaces[workspace.id] = workspace
        LOGGER.info(f"Registered workspace: {workspace.id} (Priority: {workspace.manifest.startup_priority})")

    def unregister(self, workspace_id: str) -> None:
        if workspace_id in self._workspaces:
            self._workspaces.pop(workspace_id)

    def get_workspace(self, workspace_id: str) -> Optional[BaseWorkspace]:
        return self._workspaces.get(workspace_id)

    def get_all_workspaces(self) -> List[BaseWorkspace]:
        """Returns workspaces sorted by startup priority."""
        return sorted(self._workspaces.values(), key=lambda w: w.manifest.startup_priority)