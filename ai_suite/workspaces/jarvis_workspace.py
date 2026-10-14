from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from ai_suite.core.workspace.base import BaseWorkspace
from ai_suite.core.workspace.types import WorkspaceManifest
from jarvis_ai.utils.logger import LOGGER

class JarvisWorkspace(BaseWorkspace):
    """The JARVIS AI Desktop Assistant workspace."""

    def __init__(self, event_bus, capability_manager):
        manifest = WorkspaceManifest(
            id="jarvis",
            name="JARVIS",
            version="2.0.0",
            icon="zap",
            capabilities=["vision", "voice", "camera", "automation", "ocr"],
            startup_priority=10
        )
        super().__init__(event_bus, manifest)
        self.capability_manager = capability_manager
        self.widget = None
        
    def _get_widget(self) -> QWidget:
        if self.widget is None:
            self.widget = QWidget()
        return self.widget
        
    def _do_initialize(self) -> None:
        LOGGER.info("Lazy loading JARVIS Workspace UI...")
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # PHASE 2 ARCHITECTURE: Embed the extracted JarvisContentWidget
        from jarvis_ai.ui.main_window import JarvisContentWidget
        self.content_widget = JarvisContentWidget()
            
        layout.addWidget(self.content_widget)
        LOGGER.info("JARVIS Workspace embedded successfully.")
        
    def _do_activate(self) -> None:
        pass
        
    def _do_deactivate(self) -> None:
        pass
        
    def _do_suspend(self) -> None:
        pass
            
    def _do_resume(self) -> None:
        pass
            
    def _do_shutdown(self) -> None:
        if hasattr(self, 'content_widget'):
            self.content_widget.close()
