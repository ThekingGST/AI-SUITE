"""Bottom panel — tabbed container for Terminal, Output, Problems, Mission Control."""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)
from friday_ai.core.icons import Icons
from friday_ai.core.theme import THEME
from friday_ai.ui.terminal.panel import TerminalPanel
from friday_ai.ui.panels.output_panel import OutputPanel
from friday_ai.ui.panels.problems_panel import ProblemsPanel
from friday_ai.ui.mission_control.panel import MissionControlPanel


class BottomPanel(QWidget):
    """Tabbed bottom panel: Terminal | Output | Problems | Mission Control."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomPanel")
        self._active_tab = 0
        self._tab_buttons: list[QPushButton] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab bar
        tab_bar = QWidget()
        tab_bar.setFixedHeight(32)
        tab_bar.setStyleSheet(
            f"background: {THEME.bg_surface};"
            f"border-top: {THEME.border_width}px solid {THEME.border_default};"
            f"border-bottom: {THEME.border_width}px solid {THEME.border_muted};"
        )
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(THEME.space_md, 0, THEME.space_md, 0)
        tab_layout.setSpacing(0)

        tabs = [
            ("terminal", "TERMINAL"),
            ("activity", "OUTPUT"),
            ("check", "PROBLEMS"),
            ("activity", "MISSION CONTROL"),
        ]
        for i, (icon_name, label) in enumerate(tabs):
            btn = QPushButton(f"  {label}")
            btn.setIcon(Icons.get(icon_name, color=THEME.text_muted, size=12))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._tab_style(i == 0))
            btn.clicked.connect(lambda checked=False, idx=i: self._select_tab(idx))
            self._tab_buttons.append(btn)
            tab_layout.addWidget(btn)
        tab_layout.addStretch()

        layout.addWidget(tab_bar)

        # Stack
        self._stack = QStackedWidget()
        self.terminal = TerminalPanel()
        self.output = OutputPanel()
        self.problems = ProblemsPanel()
        self.mission_control = MissionControlPanel()

        self._stack.addWidget(self.terminal)
        self._stack.addWidget(self.output)
        self._stack.addWidget(self.problems)
        self._stack.addWidget(self.mission_control)

        layout.addWidget(self._stack, stretch=1)

    def _tab_style(self, active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: transparent; color: {THEME.text_primary};"
                f" border: none; border-bottom: 2px solid {THEME.accent};"
                f" font-size: {THEME.font_size_xs}px; font-weight: bold;"
                f" padding: 0 {THEME.space_lg}px; }}"
                f"QPushButton:hover {{ background: {THEME.bg_hover}; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {THEME.text_muted};"
            f" border: none; border-bottom: 2px solid transparent;"
            f" font-size: {THEME.font_size_xs}px;"
            f" padding: 0 {THEME.space_lg}px; }}"
            f"QPushButton:hover {{ background: {THEME.bg_hover}; color: {THEME.text_secondary}; }}"
        )

    def _select_tab(self, index: int) -> None:
        self._active_tab = index
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._tab_buttons):
            btn.setStyleSheet(self._tab_style(i == index))
        if index == 0:
            self.terminal.ensure_terminal()

    def show_terminal(self) -> None:
        self._select_tab(0)
        self.terminal.ensure_terminal()
        self.show()

    def show_output(self) -> None:
        self._select_tab(1)
        self.show()

    def show_problems(self) -> None:
        self._select_tab(2)
        self.show()

    def show_mission_control(self) -> None:
        self._select_tab(3)
        self.show()
