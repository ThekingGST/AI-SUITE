"""FRIDAY status bar — dynamic contextual information.

The coloured strip at the bottom of the window displays real-time project
and file information:

    * Active workspace (JARVIS / FRIDAY / EDITH)
    * Project name
    * Transient status message / file type
    * Current filename
    * File count
    * Encoding
    * Line ending (CRLF / LF)
    * Cursor position (Ln, Col)
    * Version
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget
import sys

from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from friday_ai.services.git_service import GitService
from friday_ai.ui.editor.highlighter import get_file_type


class StatusBar(QWidget):
    """Bottom status bar with segmented information display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(THEME.status_bar_height)
        self._build_ui()
        self._connect_signals()

    # ── Construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            THEME.space_lg, 0, THEME.space_lg, 0,
        )
        layout.setSpacing(THEME.space_xl)

        # Left: workspace indicator
        self._workspace_label = self._make_label("FRIDAY", bold=True)
        layout.addWidget(self._workspace_label)

        # Left: project name
        self._project_label = self._make_label("No Project")
        layout.addWidget(self._project_label)

        # Left: status message (stretches)
        self._status_label = self._make_label("Ready")
        layout.addWidget(self._status_label, stretch=1)

        # Right: current file
        self._file_label = self._make_label("")
        layout.addWidget(self._file_label)

        # Right: file type
        self._type_label = self._make_label("")
        layout.addWidget(self._type_label)

        # Right: file count
        self._count_label = self._make_label("")
        layout.addWidget(self._count_label)

        # Right: line ending
        self._eol_label = self._make_label("")
        layout.addWidget(self._eol_label)

        # Right: encoding
        self._encoding_label = self._make_label("UTF-8")
        layout.addWidget(self._encoding_label)

        # Right: git branch
        self._git_service = GitService(self)
        self._git_label = self._make_label("")
        layout.addWidget(self._git_label)

        # Right: cursor position
        self._cursor_label = self._make_label("Ln 1, Col 1")
        layout.addWidget(self._cursor_label)

        # Right: compiler/interpreter
        self._compiler_label = self._make_label("")
        layout.addWidget(self._compiler_label)

        # Right: python version
        self._python_label = self._make_label(f"Python {sys.version.split()[0]}")
        layout.addWidget(self._python_label)

        # Right: version
        from friday_ai import __version__
        self._version_label = self._make_label(f"v{__version__}")
        layout.addWidget(self._version_label)

    def _make_label(self, text: str, *, bold: bool = False) -> QLabel:
        label = QLabel(text)
        weight = "bold" if bold else "normal"
        label.setStyleSheet(
            f"color: {THEME.text_on_accent}; "
            f"font-size: {THEME.font_size_xs}px; "
            f"font-weight: {weight}; "
            "background: transparent;"
        )
        return label

    # ── Signal handling ──────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        signals.status_message.connect(self._on_status)
        signals.cursor_position.connect(self._on_cursor)
        signals.workspace_switched.connect(self._on_workspace)
        signals.project_opened.connect(self._on_project_opened)
        signals.project_closed.connect(self._on_project_closed)
        signals.project_stats.connect(self._on_project_stats)
        signals.file_opened.connect(self._on_file_opened)
        signals.file_closed.connect(self._on_file_closed)
        signals.file_saved.connect(self._on_file_saved)
        signals.compiler_updated.connect(self._on_compiler_updated)

    def _on_compiler_updated(self, path: str) -> None:
        self._compiler_label.setText(path)

    def _on_status(self, message: str) -> None:
        self._status_label.setText(message)

    def _on_cursor(self, line: int, col: int) -> None:
        self._cursor_label.setText(f"Ln {line}, Col {col}")

    def _on_workspace(self, name: str) -> None:
        display = {"jarvis": "JARVIS", "friday": "FRIDAY", "edith": "EDITH"}
        self._workspace_label.setText(display.get(name, name.upper()))

    def _update_git_status(self) -> None:
        import shutil
        if not shutil.which("git"):
            self._git_label.setText("Git not installed")
            return
            
        branch = self._git_service.get_branch()
        if branch:
            changed = self._git_service.get_changed_files_count()
            if changed > 0:
                self._git_label.setText(f"git: {branch} ({changed} changed)")
            else:
                self._git_label.setText(f"git: {branch}")
        else:
            if self._git_service.is_git_repo():
                self._git_label.setText("git: detached")
            else:
                self._git_label.setText("")

    def _on_project_opened(self, path: str) -> None:
        self._project_label.setText(Path(path).name)
        self._git_service.set_project_root(path)
        self._update_git_status()

    def _on_project_closed(self) -> None:
        self._project_label.setText("No Project")
        self._file_label.setText("")
        self._type_label.setText("")
        self._count_label.setText("")
        self._eol_label.setText("")
        self._git_label.setText("")

    def _on_project_stats(self, name: str, count: int) -> None:
        self._count_label.setText(f"{count} files")

    def _on_file_opened(self, path: str) -> None:
        p = Path(path)
        self._file_label.setText(p.name)
        self._type_label.setText(get_file_type(p.suffix))
        self._cursor_label.setText("Ln 1, Col 1")
        self._encoding_label.setText("UTF-8")
        # Detect line ending
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if "\r\n" in content:
                self._eol_label.setText("CRLF")
            else:
                self._eol_label.setText("LF")
        except OSError:
            self._eol_label.setText("LF")

    def _on_file_closed(self, path: str) -> None:
        self._file_label.setText("")
        self._type_label.setText("")
        self._eol_label.setText("")

    def _on_file_saved(self, path: str) -> None:
        self._status_label.setText(f"Saved {Path(path).name}")
        self._update_git_status()
