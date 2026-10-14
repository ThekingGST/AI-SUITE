"""Terminal panel — tabbed container for multiple terminal sessions."""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)
from friday_ai.core.icons import Icons
from friday_ai.core.theme import THEME
from friday_ai.services.terminal_service import detect_shells
from friday_ai.ui.terminal.terminal_widget import TerminalWidget


class TerminalPanel(QWidget):
    """Tabbed terminal container."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._shells = detect_shells()
        self._tabs: list[tuple[str, TerminalWidget]] = []
        self._default_cwd = ""
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar
        tab_bar = QWidget()
        tab_bar.setStyleSheet(
            f"background: {THEME.bg_surface};"
            f"border-bottom: {THEME.border_width}px solid {THEME.border_muted};"
        )
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(THEME.space_md, 0, THEME.space_md, 0)
        tab_layout.setSpacing(0)

        self._tab_layout = tab_layout

        # New terminal button
        new_btn = QPushButton("+")
        new_btn.setFixedSize(28, 28)
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setToolTip("New Terminal")
        new_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {THEME.text_secondary};"
            f" border: none; font-size: {THEME.font_size_lg}px; border-radius: {THEME.radius_sm}px; }}"
            f"QPushButton:hover {{ background: {THEME.bg_hover}; color: {THEME.text_primary}; }}"
        )
        new_btn.clicked.connect(self._add_terminal)
        tab_layout.addStretch()
        tab_layout.addWidget(new_btn)

        layout.addWidget(tab_bar)

        # Stack
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background: {THEME.bg_inset};")
        layout.addWidget(self._stack, stretch=1)

    def _add_terminal(self, shell_idx: int = 0) -> None:
        if not self._shells:
            return
        name, path = self._shells[min(shell_idx, len(self._shells) - 1)]
        cwd = getattr(self, "_default_cwd", "")
        widget = TerminalWidget(path, cwd)
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)

        idx = len(self._tabs)
        label = f"{name} {idx + 1}"
        self._tabs.append((label, widget))

        # Add tab button (before the stretch and + button)
        btn = QPushButton(label)
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {THEME.text_secondary};"
            f" border: none; padding: 0 {THEME.space_lg}px; font-size: {THEME.font_size_xs}px; }}"
            f"QPushButton:hover {{ background: {THEME.bg_hover}; color: {THEME.text_primary}; }}"
        )
        btn.clicked.connect(lambda checked=False, w=widget: self._stack.setCurrentWidget(w))
        self._tab_layout.insertWidget(self._tab_layout.count() - 2, btn)

    def set_cwd(self, path: str) -> None:
        """Set working directory for new terminals."""
        self._default_cwd = path

    def ensure_terminal(self) -> None:
        """Create a terminal if none exists."""
        if not self._tabs:
            self._add_terminal()

    def write_to_active(self, text: str) -> None:
        """Write text to the active terminal."""
        widget = self._stack.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget._session.write(text)

    def clear_active(self) -> None:
        widget = self._stack.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget.clear_terminal()

    def kill_active(self) -> None:
        widget = self._stack.currentWidget()
        if isinstance(widget, TerminalWidget):
            widget.kill_process()
