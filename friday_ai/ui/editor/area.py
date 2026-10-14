"""Editor area — manages tabs and their content widgets.

The editor area is the central panel of the IDE.  It contains the tab bar at
the top, an optional search/replace bar, and a stacked widget below it that
displays the content of the active tab.

Features:
    * Opens text files in CodeEditor (with syntax highlighting)
    * Opens image files in ImageView (preview)
    * Tracks open files by normalized path (no duplicates)
    * Dirty indicator on tab titles
    * Save (Ctrl+S), Save As (Ctrl+Shift+S)
    * Find (Ctrl+F), Replace (Ctrl+H)
    * Close tab with confirmation when dirty
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from friday_ai.ui.editor.code_editor import CodeEditor
from friday_ai.ui.editor.image_view import ImageView, is_image_file
from friday_ai.ui.editor.search_bar import SearchBar
from friday_ai.ui.editor.tab_bar import TabBar
from friday_ai.ui.editor.welcome import WelcomeTab
from friday_ai.ui.editor.highlighter import get_file_type, get_line_ending
from shared.logger import get_logger

LOG = get_logger("friday.editor")

# Maximum file size to open (5 MB).
_MAX_FILE_SIZE = 5 * 1024 * 1024


class EditorArea(QWidget):
    """Central editor area: tab bar + search bar + content stack."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("editorArea")
        self._open_paths: dict[str, int] = {}  # normalized path → tab index
        self._tab_widgets: list[QWidget] = []   # widget at each tab index
        self._build_ui()
        self._setup_shortcuts()
        self._connect_signals()

    # ── Construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar
        self._tab_bar = TabBar()
        layout.addWidget(self._tab_bar)

        # Search bar (initially hidden)
        self._search_bar = SearchBar()
        layout.addWidget(self._search_bar)

        # Content stack
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {THEME.bg_base};")
        layout.addWidget(self._stack, stretch=1)

        # Welcome tab is always the first
        self._welcome = WelcomeTab()
        self._stack.addWidget(self._welcome)
        self._tab_widgets.append(self._welcome)

        self._tab_bar.add_tab("Welcome", icon_name="code", closable=False)

        # Connect tab events
        self._tab_bar.tab_selected.connect(self._on_tab_selected)
        self._tab_bar.tab_closed.connect(self._on_tab_close_requested)

    def _setup_shortcuts(self) -> None:
        # Save
        save = QAction("Save", self)
        save.setShortcut(QKeySequence("Ctrl+S"))
        save.triggered.connect(self._save_current)
        self.addAction(save)

        # Save As
        save_as = QAction("Save As", self)
        save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as.triggered.connect(self._save_as_current)
        self.addAction(save_as)

        # Find
        find = QAction("Find", self)
        find.setShortcut(QKeySequence("Ctrl+F"))
        find.triggered.connect(self._open_find)
        self.addAction(find)

        # Replace
        replace = QAction("Replace", self)
        replace.setShortcut(QKeySequence("Ctrl+H"))
        replace.triggered.connect(self._open_replace)
        self.addAction(replace)

    def _connect_signals(self) -> None:
        signals.file_open_requested.connect(self._open_file)

    # ── File opening ─────────────────────────────────────────────────────

    def _open_file(self, path: str) -> None:
        """Open a file in a new tab, or focus it if already open."""
        norm_path = str(Path(path).resolve())

        # If already open, just focus that tab.
        if norm_path in self._open_paths:
            tab_index = self._open_paths[norm_path]
            self._tab_bar.select(tab_index)
            signals.file_opened.emit(norm_path)
            self._emit_file_info(norm_path)
            return

        p = Path(norm_path)
        if not p.is_file():
            signals.mission_update.emit("ERROR", f"Not a file: {p.name}")
            return

        if p.stat().st_size > _MAX_FILE_SIZE:
            signals.mission_update.emit(
                "WARN", f"File too large: {p.name} ({p.stat().st_size // 1024}KB)",
            )
            return

        # Create widget based on file type
        if is_image_file(norm_path):
            widget = ImageView(norm_path)
            icon_name = "file-text"
        else:
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                LOG.warning("Failed to read file %s: %s", path, exc)
                signals.mission_update.emit("ERROR", f"Cannot read: {p.name}")
                return

            widget = CodeEditor(content, file_path=norm_path)
            widget.dirty_changed.connect(
                lambda dirty, idx=len(self._tab_widgets): self._on_dirty_changed(idx, dirty),
            )
            icon_name = "file-text"

        self._stack.addWidget(widget)
        self._tab_widgets.append(widget)
        tab_index = len(self._tab_widgets) - 1
        self._open_paths[norm_path] = tab_index

        self._tab_bar.add_tab(p.name, icon_name=icon_name)
        self._stack.setCurrentWidget(widget)

        # Bind search bar to this editor
        if isinstance(widget, CodeEditor):
            self._search_bar.set_editor(widget)

        signals.file_opened.emit(norm_path)
        signals.mission_update.emit("OPEN", f"Opened {p.name}")
        self._emit_file_info(norm_path)
        LOG.info("Opened file: %s", norm_path)

    def _emit_file_info(self, path: str) -> None:
        """Emit file type and line ending info for the status bar."""
        ext = Path(path).suffix
        file_type = get_file_type(ext)
        signals.status_message.emit(f"{file_type}")

    # ── Editor Access ────────────────────────────────────────────────────

    def get_editor_for_file(self, file_path: str) -> CodeEditor | None:
        """Returns the CodeEditor instance for a given file path if it is open."""
        norm = str(Path(file_path).resolve())
        idx = self._open_paths.get(norm)
        if idx is not None:
            widget = self._tab_widgets[idx]
            if isinstance(widget, CodeEditor):
                return widget
        return None

    # ── Tab events ───────────────────────────────────────────────────────

    def _on_tab_selected(self, index: int) -> None:
        if 0 <= index < len(self._tab_widgets):
            widget = self._tab_widgets[index]
            self._stack.setCurrentWidget(widget)
            # Update search bar binding
            if isinstance(widget, CodeEditor):
                self._search_bar.set_editor(widget)
            # Re-emit file info for this tab
            for path, idx in self._open_paths.items():
                if idx == index:
                    signals.file_opened.emit(path)
                    self._emit_file_info(path)
                    break

    def _on_tab_close_requested(self, index: int) -> None:
        if index < 0 or index >= len(self._tab_widgets):
            return

        widget = self._tab_widgets[index]

        # Check for dirty state
        if isinstance(widget, CodeEditor) and widget.dirty:
            name = Path(widget.file_path).name if widget.file_path else "Untitled"
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"'{name}' has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Save:
                if not widget.save():
                    return

        # Remove from tracking
        path_to_remove = None
        for p, idx in self._open_paths.items():
            if idx == index:
                path_to_remove = p
                break
        if path_to_remove:
            del self._open_paths[path_to_remove]
            signals.file_closed.emit(path_to_remove)

        # Remove widget
        self._tab_widgets.pop(index)
        self._stack.removeWidget(widget)
        widget.deleteLater()

        # Rebuild index mapping
        new_map: dict[str, int] = {}
        for p, old_idx in self._open_paths.items():
            if old_idx > index:
                new_map[p] = old_idx - 1
            else:
                new_map[p] = old_idx
        self._open_paths = new_map

        # If no tabs left, show welcome
        if self._tab_bar.count == 0:
            self._welcome = WelcomeTab()
            self._stack.addWidget(self._welcome)
            self._tab_widgets.append(self._welcome)
            self._tab_bar.add_tab("Welcome", icon_name="code", closable=False)

    # ── Dirty indicator ──────────────────────────────────────────────────

    def _on_dirty_changed(self, tab_index: int, dirty: bool) -> None:
        """Update tab title with dirty indicator."""
        if tab_index >= len(self._tab_widgets):
            return
        widget = self._tab_widgets[tab_index]
        if isinstance(widget, CodeEditor) and widget.file_path:
            name = Path(widget.file_path).name
            if dirty:
                self._tab_bar.set_tab_title(tab_index, f"\u25cf {name}")
            else:
                self._tab_bar.set_tab_title(tab_index, name)

    # ── Save ─────────────────────────────────────────────────────────────

    def _save_current(self) -> None:
        widget = self._current_editor()
        if widget is not None:
            widget.save()

    def _save_as_current(self) -> None:
        widget = self._current_editor()
        if widget is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", widget.file_path or "",
        )
        if path:
            widget.save_as(path)

    # ── Search ───────────────────────────────────────────────────────────

    def _open_find(self) -> None:
        editor = self._current_editor()
        if editor:
            self._search_bar.set_editor(editor)
            self._search_bar.open_find()

    def _open_replace(self) -> None:
        editor = self._current_editor()
        if editor:
            self._search_bar.set_editor(editor)
            self._search_bar.open_replace()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _current_editor(self) -> CodeEditor | None:
        widget = self._stack.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    # ── Legacy API ───────────────────────────────────────────────────────

    def open_document(self, title: str, content: str) -> None:
        """Open a new document tab with the given content (legacy)."""
        editor = CodeEditor(content)
        self._stack.addWidget(editor)
        self._tab_widgets.append(editor)
        self._tab_bar.add_tab(title)
        self._stack.setCurrentWidget(editor)
