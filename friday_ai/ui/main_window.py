"""FRIDAY main window — the thin composition shell with project integration.

This file composes all panels into a resizable layout using QSplitters,
integrates the project manager and persistence services, and handles
keyboard shortcuts.

Signal flow for opening a project:

    1. User clicks "Open Project" (welcome tab or Ctrl+O)
    2. ``project_open_requested`` is emitted with the raw folder path
    3. MainWindow routes through ProjectManager for validation & scanning
    4. ProjectManager emits ``project_opened`` on success
    5. Explorer, status bar, mission control react to ``project_opened``

Layout::

    +-------+--------------------+--------------+
    |       |                    |              |
    | Side  |   Editor Area      |  Workspace   |
    | bar   |                    |  Panel       |
    |       |                    |              |
    |       +--------------------+--------------+
    |       |   Mission Control                 |
    +-------+-----------------------------------+
    |   Status Bar                              |
    +-------------------------------------------+
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.config import CONFIG
from friday_ai.core.signals import signals
from friday_ai.services.persistence import WorkspacePersistence
from friday_ai.services.project_manager import ProjectManager
from friday_ai.services.toolchain_manager import ToolchainManager
from friday_ai.services.environment_manager import EnvironmentManager
from friday_ai.services.build_manager import BuildManager
from friday_ai.services.execution_manager import ExecutionManager
from friday_ai.ui.editor.area import EditorArea
from friday_ai.ui.menu_bar import FridayMenuBar
from friday_ai.ui.panels.bottom_panel import BottomPanel
from friday_ai.ui.panels.search_panel import SearchPanel
from friday_ai.ui.sidebar.panel import SidebarPanel
from friday_ai.ui.status_bar.bar import StatusBar
from friday_ai.ui.workspace_panel.panel import WorkspacePanel
from friday_ai.brain.project_brain import ProjectBrain
from friday_ai.brain.workspace_context import WorkspaceContext
from friday_ai.brain.context_builder import ContextBuilder
from friday_ai.brain.memory import ConversationMemory
from friday_ai.brain.prompt_controller import PromptController
from shared.logger import get_logger

LOG = get_logger("friday.window")


class MainWindow(QMainWindow):
    """Top-level application window.

    Composes all UI panels, integrates the project manager and persistence
    services, and manages keyboard shortcuts.
    """

    def __init__(
        self,
        persistence: WorkspacePersistence | None = None,
    ) -> None:
        super().__init__()
        self._persistence = persistence or WorkspacePersistence()
        self._project_mgr = ProjectManager(parent=self)
        self._toolchain_mgr = ToolchainManager(parent=self)
        self._toolchain_mgr.detect_all()  # Start background discovery
        self._env_mgr = EnvironmentManager(self._toolchain_mgr, parent=self)
        self._build_mgr = BuildManager(self._toolchain_mgr, parent=self)
        self._execution_mgr = ExecutionManager(parent=self)
        
        from friday_ai.services.provider_manager import ProviderManager
        self._provider_mgr = ProviderManager(self._persistence, parent=self)
        
        # ── AI Brain ──
        self._brain = ProjectBrain(parent=self)
        self._ws_context = WorkspaceContext(parent=self)
        self._ctx_builder = ContextBuilder(self._brain, self._ws_context)
        self._memory = ConversationMemory()
        
        from friday_ai.brain.ai_session import AISession
        from friday_ai.brain.model_registry import ModelRegistry
        from friday_ai.brain.ai_orchestrator import AIOrchestrator
        from friday_ai.brain.prompt_controller import PromptController
        
        self._ai_session = AISession(id="default", memory=self._memory)
        self._registry = ModelRegistry()
        self._orchestrator = AIOrchestrator(
            session=self._ai_session,
            context_builder=self._ctx_builder,
            provider_manager=self._provider_mgr,
            registry=self._registry,
            parent=self
        )
        self._prompt_controller = PromptController(
            orchestrator=self._orchestrator,
            parent=self
        )
        
        from friday_ai.brain.ai_actions.action_executor import ActionExecutor
        self._action_executor = ActionExecutor(self._orchestrator, parent=self)
        
        # Inject the session into action requests dynamically when received
        def _on_action_requested(request):
            request.session = self._ai_session
            self._action_executor.execute(request)
            
        from friday_ai.core.signals import signals
        signals.ai_action_requested.connect(_on_action_requested)
        
        from friday_ai.brain.editing.editing_engine import EditingEngine
        self._editing_engine = EditingEngine(parent=self)
        
        def _on_diff_preview(change_set):
            from friday_ai.ui.dialogs.diff_preview_dialog import DiffPreviewDialog
            dlg = DiffPreviewDialog(change_set, parent=self)
            dlg.exec()
            
        def _on_diff_apply(change_set):
            from friday_ai.brain.editing.apply_engine import ApplyEngine
            editor = self._editor_area.get_editor_for_file(change_set.file_path)
            if not editor:
                from shared.logger import get_logger
                get_logger("friday.main").error("Could not find editor for %s", change_set.file_path)
                return
            engine = ApplyEngine(editor)
            if engine.apply(change_set):
                signals.status_message.emit("AI edits applied successfully.")
            else:
                signals.status_message.emit("Failed to apply AI edits.")
                
        signals.diff_preview_requested.connect(_on_diff_preview)
        signals.diff_apply_requested.connect(_on_diff_apply)
        
        self._configure_window()
        
        # Menu bar
        self._menu_bar = FridayMenuBar(self)
        self.setMenuBar(self._menu_bar)
        
        self._build_layout()
        self._setup_shortcuts()
        self._connect_signals()
        self._restore_state()

    # ── Window setup ─────────────────────────────────────────────────────

    def _configure_window(self) -> None:
        self.setWindowTitle(CONFIG.window.title)
        self.resize(CONFIG.window.width, CONFIG.window.height)
        self.setMinimumSize(CONFIG.window.min_width, CONFIG.window.min_height)

    # ── Layout ───────────────────────────────────────────────────────────

    def _build_layout(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Vertical splitter: [top panels] / [mission control]
        self._v_splitter = QSplitter(Qt.Vertical)

        # Horizontal splitter: sidebar / editor / workspace panel
        self._h_splitter = QSplitter(Qt.Horizontal)

        self._sidebar = SidebarPanel()
        self._editor = EditorArea()
        self._workspace_panel = WorkspacePanel(provider_manager=self._provider_mgr)

        self._h_splitter.addWidget(self._sidebar)
        self._h_splitter.addWidget(self._editor)
        self._h_splitter.addWidget(self._workspace_panel)

        # Default proportions
        layout_cfg = CONFIG.layout
        total_width = CONFIG.window.width
        sidebar_w = layout_cfg.sidebar_width + layout_cfg.explorer_width
        workspace_w = layout_cfg.workspace_panel_width
        editor_w = total_width - sidebar_w - workspace_w
        self._h_splitter.setSizes([sidebar_w, editor_w, workspace_w])

        self._h_splitter.setCollapsible(0, False)
        self._h_splitter.setCollapsible(1, False)
        self._h_splitter.setCollapsible(2, False)

        self._v_splitter.addWidget(self._h_splitter)

        # Bottom Panel
        self._bottom_panel = BottomPanel()
        self._v_splitter.addWidget(self._bottom_panel)

        editor_h = CONFIG.window.height - layout_cfg.mission_control_height
        self._v_splitter.setSizes([editor_h, layout_cfg.mission_control_height])
        self._v_splitter.setCollapsible(0, False)
        self._v_splitter.setCollapsible(1, False)

        root.addWidget(self._v_splitter, stretch=1)

        # Status bar
        self._status_bar = StatusBar()
        root.addWidget(self._status_bar)

    # ── Keyboard shortcuts ───────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        # Open Project
        open_action = QAction("Open Project", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_project_shortcut)
        self.addAction(open_action)

        # New Project
        new_proj_action = QAction("New Project", self)
        new_proj_action.setShortcut(QKeySequence("Ctrl+N"))
        new_proj_action.triggered.connect(lambda: signals.project_create_requested.emit())
        self.addAction(new_proj_action)

        # Run Project
        run_proj_action = QAction("Run Project", self)
        run_proj_action.setShortcut(QKeySequence("F5"))
        run_proj_action.triggered.connect(lambda: signals.run_project_requested.emit())
        self.addAction(run_proj_action)

        # Toggle Terminal
        toggle_term_action = QAction("Toggle Terminal", self)
        toggle_term_action.setShortcut(QKeySequence("Ctrl+`"))
        toggle_term_action.triggered.connect(
            lambda: self._bottom_panel.setVisible(not self._bottom_panel.isVisible())
        )
        self.addAction(toggle_term_action)

    # ── Signal connections ───────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # UI components emit project_open_requested; we route through the
        # project manager which validates, scans, and emits project_opened.
        signals.project_open_requested.connect(self._on_open_requested)
        signals.project_opened.connect(self._on_project_opened)
        signals.project_create_requested.connect(self._on_create_project)

        # Connect execution manager outputs to bottom panel
        self._execution_mgr.output_ready.connect(self._on_run_output)
        self._execution_mgr.diagnostic_available.connect(self._on_diagnostic)
        
        signals.run_stop_requested.connect(self._execution_mgr.stop_execution)

        # Editor jumps
        signals.goto_line_requested.connect(self._on_goto_line_requested)

    def _on_goto_line_requested(self, line: int, col: int) -> None:
        from friday_ai.ui.editor.code_editor import CodeEditor
        from PyQt5.QtGui import QTextCursor
        editor = self._editor._stack.currentWidget()
        if isinstance(editor, CodeEditor):
            cursor = editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, n=max(0, line-1))
            if col > 0:
                cursor.movePosition(QTextCursor.Right, n=col-1)
            editor.setTextCursor(cursor)
            editor.ensureCursorVisible()
            editor.setFocus()

    def _on_run_output(self, text: str, category: str = "system") -> None:
        self._bottom_panel.output.append(text, category)
        self._bottom_panel.show_output()

    def _on_diagnostic(self, friendly_msg: str, raw_stderr: str) -> None:
        self._bottom_panel.output.append(f"\n[Diagnostic]\n{friendly_msg}\n\n", "error")
        self._bottom_panel.output.show_explain_button(friendly_msg, raw_stderr)

    def open_settings(self) -> None:
        """Open the Settings page in the editor."""
        from friday_ai.ui.editor.settings_page import SettingsPage
        # Check if already open
        for i in range(self._editor._stack.count()):
            widget = self._editor._stack.widget(i)
            if isinstance(widget, SettingsPage):
                self._editor._tab_bar.select(i)
                return
        
        # Open new tab
        settings = SettingsPage()
        self._editor._stack.addWidget(settings)
        idx = self._editor._stack.count() - 1
        self._editor._tab_widgets.append(settings)
        self._editor._tab_bar.add_tab("Settings", icon_name="settings", closable=True)
        self._editor._tab_bar.select(idx)

    def show_search(self) -> None:
        """Show project-wide search."""
        self._sidebar.show_search()

    def show_outline(self) -> None:
        """Show outline panel."""
        self._sidebar.show_outline()

    def run_current_file(self) -> None:
        """Run the file currently active in the editor."""
        active_tab = self._editor._stack.currentWidget()
        from friday_ai.ui.editor.code_editor import CodeEditor
        if isinstance(active_tab, CodeEditor):
            if active_tab.dirty:
                active_tab.save()
            if active_tab.file_path:
                self._bottom_panel.output.clear()
                self._bottom_panel.show_output()
                self._execution_mgr.run_file(active_tab.file_path)

    def new_terminal(self) -> None:
        """Open a new terminal."""
        self._bottom_panel.show_terminal()
        self._bottom_panel.terminal._add_terminal()

    def _on_open_requested(self, path: str) -> None:
        """Validate and open a project through the project manager."""
        self._project_mgr.open_project(path)

    def _on_project_opened(self, path: str) -> None:
        """Persist state and detect environment after a project is opened."""
        self._save_state()
        self._bottom_panel.terminal.set_cwd(path)
        # Detect project type and environment
        project_type = self._project_mgr.detect_project_type(Path(path))
        signals.project_type_detected.emit(path, project_type.value)
        env = self._env_mgr.detect_project_environment(Path(path))
        if env:
            signals.environment_changed.emit(env.name, env.interpreter_path)

    def _on_create_project(self) -> None:
        """Show the project creation wizard."""
        from friday_ai.ui.dialogs.project_wizard import ProjectWizard
        wizard = ProjectWizard(self._project_mgr, parent=self)
        wizard.exec()

    def _show_environment_panel(self) -> None:
        """Show the environment management panel."""
        from friday_ai.ui.dialogs.environment_panel import EnvironmentPanel
        panel = EnvironmentPanel(self._toolchain_mgr, self._env_mgr, parent=self)
        panel.exec()

    # ── Open Project dialog ──────────────────────────────────────────────

    def _on_open_project_shortcut(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Open Project", "",
            QFileDialog.ShowDirsOnly,
        )
        if path:
            self._project_mgr.open_project(path)

    # ── Persistence ──────────────────────────────────────────────────────

    def _restore_state(self) -> None:
        """Restore window geometry and layout from persistence."""
        ws = self._persistence.window_state
        if ws.get("maximized", False):
            self.showMaximized()
        elif ws.get("x", -1) >= 0:
            self.move(ws["x"], ws["y"])
            self.resize(ws["width"], ws["height"])

        ls = self._persistence.layout_state
        if ls.get("h_splitter"):
            self._h_splitter.setSizes(ls["h_splitter"])
        if ls.get("v_splitter"):
            self._v_splitter.setSizes(ls["v_splitter"])

        # Restore recent projects to the project manager.
        self._project_mgr.recent_projects = self._persistence.recent_projects

        # Re-open the last project.
        last = self._persistence.last_project
        if last and Path(last).is_dir():
            LOG.info("Restoring last project: %s", last)
            self._project_mgr.open_project(last)

    def _save_state(self) -> None:
        """Persist current window and layout state."""
        self._persistence.window_state = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "maximized": self.isMaximized(),
        }
        self._persistence.layout_state = {
            "h_splitter": self._h_splitter.sizes(),
            "v_splitter": self._v_splitter.sizes(),
        }
        self._persistence.recent_projects = self._project_mgr.recent_projects
        if self._project_mgr.current_path:
            self._persistence.last_project = str(self._project_mgr.current_path)
        self._persistence.save()

    def closeEvent(self, event) -> None:
        """Save state before the window closes."""
        self._save_state()
        super().closeEvent(event)
