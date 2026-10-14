"""Workspace state tracking for the AI.

Keeps an up-to-date representation of what the user is currently doing.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

from PyQt5.QtCore import QObject

from friday_ai.core.signals import signals
from friday_ai.ui.editor.highlighter import get_file_type
from shared.logger import get_logger

LOG = get_logger("friday.workspace")


@dataclass
class WorkspaceState:
    """A snapshot of the current workspace state.

    This is the canonical state object consumed by the AI context builder.
    It aggregates information from all IDE subsystems into a single snapshot.
    """

    # ── Workspace context ────────────────────────────────────────────────
    current_project: str | None = None
    current_file: str | None = None
    active_language: str | None = None
    cursor_line: int = 0
    cursor_column: int = 0
    selected_code: str = ""
    open_tabs: list[str] = field(default_factory=list)
    recent_files: list[str] = field(default_factory=list)
    recent_searches: list[str] = field(default_factory=list)

    # ── Project context (Milestone 4) ────────────────────────────────────
    project_type: str | None = None

    # ── Runtime context (Milestone 4) ────────────────────────────────────
    active_runtime: str | None = None          # "Python 3.11.4"
    active_interpreter: str | None = None      # "/path/to/venv/python"

    # ── Environment context (Milestone 4) ────────────────────────────────
    active_environment: str | None = None      # "myproject-venv"
    installed_packages: list[str] = field(default_factory=list)

    # ── Execution context (Milestone 4) ──────────────────────────────────
    last_execution_exit_code: int | None = None
    last_execution_output: str = ""


class WorkspaceContext(QObject):
    """Tracks workspace state by subscribing to core signals."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._state = WorkspaceState()
        self._connect_signals()

    def _connect_signals(self) -> None:
        signals.project_opened.connect(self._on_project_opened)
        signals.project_closed.connect(self._on_project_closed)
        signals.file_opened.connect(self._on_file_opened)
        signals.file_closed.connect(self._on_file_closed)
        signals.cursor_position.connect(self._on_cursor_position)
        signals.selection_changed.connect(self._on_selection_changed)
        signals.search_requested.connect(self._on_search_requested)
        # Milestone 4 signals
        signals.project_type_detected.connect(self._on_project_type_detected)
        signals.environment_changed.connect(self._on_environment_changed)
        signals.execution_completed.connect(self._on_execution_completed)

    def get_context(self) -> WorkspaceState:
        """Get a snapshot of the current state."""
        # Return a copy to avoid accidental mutation
        import copy
        return copy.deepcopy(self._state)

    def _on_project_opened(self, path: str) -> None:
        self._state.current_project = path
        self._state.open_tabs.clear()
        
    def _on_project_closed(self) -> None:
        self._state.current_project = None
        self._state.current_file = None
        self._state.active_language = None
        self._state.open_tabs.clear()
        
    def _on_file_opened(self, path: str) -> None:
        norm_path = str(Path(path).resolve())
        self._state.current_file = norm_path
        self._state.active_language = get_file_type(Path(path).suffix)
        
        if norm_path not in self._state.open_tabs:
            self._state.open_tabs.append(norm_path)
            
        if norm_path in self._state.recent_files:
            self._state.recent_files.remove(norm_path)
        self._state.recent_files.insert(0, norm_path)
        self._state.recent_files = self._state.recent_files[:20]
        
    def _on_file_closed(self, path: str) -> None:
        norm_path = str(Path(path).resolve())
        if norm_path in self._state.open_tabs:
            self._state.open_tabs.remove(norm_path)
        if self._state.current_file == norm_path:
            self._state.current_file = None
            self._state.active_language = None

    def _on_cursor_position(self, line: int, col: int) -> None:
        self._state.cursor_line = line
        self._state.cursor_column = col

    def _on_selection_changed(self, text: str) -> None:
        self._state.selected_code = text

    def _on_search_requested(self, query: str) -> None:
        if query in self._state.recent_searches:
            self._state.recent_searches.remove(query)
        self._state.recent_searches.insert(0, query)
        self._state.recent_searches = self._state.recent_searches[:10]

    # ── Milestone 4 handlers ─────────────────────────────────────────────

    def _on_project_type_detected(self, path: str, project_type: str) -> None:
        if self._state.current_project == path:
            self._state.project_type = project_type

    def _on_environment_changed(self, env_name: str, interpreter_path: str) -> None:
        self._state.active_environment = env_name
        self._state.active_interpreter = interpreter_path

    def _on_execution_completed(self, event: object) -> None:
        """Capture last execution result for AI context."""
        self._state.last_execution_exit_code = getattr(event, "exit_code", None)
        stdout = getattr(event, "stdout", "")
        stderr = getattr(event, "stderr", "")
        # Truncate to last 500 chars to avoid context bloat
        combined = (stdout + stderr).strip()
        self._state.last_execution_output = combined[-500:] if len(combined) > 500 else combined
