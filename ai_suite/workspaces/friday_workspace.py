from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from ai_suite.core.workspace.base import BaseWorkspace
from ai_suite.core.workspace.types import WorkspaceManifest
from jarvis_ai.utils.logger import LOGGER

class FridayWorkspace(BaseWorkspace):
    """The FRIDAY AI IDE workspace."""

    def __init__(self, event_bus, capability_manager, session_manager, project_manager):
        manifest = WorkspaceManifest(
            id="friday",
            name="FRIDAY",
            version="2.0.0",
            icon="code",
            capabilities=["ide", "git", "terminal", "project_analysis", "code_actions"],
            startup_priority=50
        )
        super().__init__(event_bus, manifest)
        self.capability_manager = capability_manager
        self.session_manager = session_manager
        self.project_manager = project_manager
        
        self.widget = None
        
    def _get_widget(self) -> QWidget:
        if self.widget is None:
            self.widget = QWidget()
        return self.widget

    def _do_initialize(self) -> None:
        """Lazy loads FRIDAY IDE."""
        LOGGER.info("Lazy loading FRIDAY Workspace UI...")
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # PHASE 1 COMPATIBILITY: Embed the legacy MainWindow directly
        from friday_ai.ui.main_window import MainWindow
        from friday_ai.core.theme import build_stylesheet
        self.main_window = MainWindow()
        
        # Strip window decorations so it can be embedded in our StackedWidget
        self.main_window.setWindowFlags(Qt.Widget)
        self.main_window.setStyleSheet(build_stylesheet())
        
        layout.addWidget(self.main_window)
        LOGGER.info("FRIDAY Workspace embedded successfully.")

    def _do_activate(self) -> None:
        pass

    def _do_deactivate(self) -> None:
        pass

    def _do_suspend(self) -> None:
        pass

    def _do_resume(self) -> None:
        pass
        
    def _do_shutdown(self) -> None:
        if hasattr(self, 'main_window'):
            self.main_window.close()
