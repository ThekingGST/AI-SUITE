from abc import ABC, abstractmethod
from typing import Any
from PyQt5.QtWidgets import QWidget
from ai_suite.core.workspace.types import WorkspaceManifest, WorkspaceSession, WorkspaceContext
from jarvis_ai.utils.logger import LOGGER

class BaseWorkspace(ABC):
    """The foundational contract for all AI Suite Workspaces."""
    
    def __init__(self, event_bus: Any, manifest: WorkspaceManifest):
        self.event_bus = event_bus
        self.manifest = manifest
        self.session = WorkspaceSession()
        self.context = WorkspaceContext(workspace_id=manifest.id)
        self.is_initialized = False
        self.is_active = False
        
    @property
    def id(self) -> str:
        return self.manifest.id
        
    def get_widget(self) -> QWidget:
        """Returns the main UI widget for this workspace."""
        return self._get_widget()
        
    @abstractmethod
    def _get_widget(self) -> QWidget:
        pass

    def initialize(self) -> None:
        """Called once during the first activation (lazy loading)."""
        if self.is_initialized:
            return
        LOGGER.info(f"[{self.id}] Initializing workspace...")
        self._do_initialize()
        self.is_initialized = True

    @abstractmethod
    def _do_initialize(self) -> None:
        pass

    def activate(self) -> None:
        """Called when the workspace becomes the active view."""
        if not self.is_initialized:
            self.initialize()
            
        LOGGER.info(f"[{self.id}] Activating workspace...")
        self.is_active = True
        self._do_activate()
        self.event_bus.workspaceActivated.emit(self.id)

    @abstractmethod
    def _do_activate(self) -> None:
        pass

    def deactivate(self) -> None:
        """Called when swapping away from the workspace (a full deactivation if needed)."""
        LOGGER.info(f"[{self.id}] Deactivating workspace...")
        self.is_active = False
        self._do_deactivate()
        self.event_bus.workspaceDeactivated.emit(self.id)

    @abstractmethod
    def _do_deactivate(self) -> None:
        pass

    def suspend(self) -> None:
        """Called to pause intensive background tasks when hidden."""
        if not self.is_active:
            return
            
        LOGGER.info(f"[{self.id}] Suspending workspace...")
        self._do_suspend()
        self.event_bus.workspaceSuspended.emit(self.id)
        
    @abstractmethod
    def _do_suspend(self) -> None:
        pass

    def resume(self) -> None:
        """Called to unpause tasks when returning."""
        LOGGER.info(f"[{self.id}] Resuming workspace...")
        self._do_resume()
        self.event_bus.workspaceResumed.emit(self.id)
        self.activate() # Resume usually implies activation

    @abstractmethod
    def _do_resume(self) -> None:
        pass

    def shutdown(self) -> None:
        """Called during application exit."""
        LOGGER.info(f"[{self.id}] Shutting down workspace...")
        self._do_shutdown()

    @abstractmethod
    def _do_shutdown(self) -> None:
        pass