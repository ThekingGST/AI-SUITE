"""Problems panel — displays errors and warnings.

Designed to be extensible for future linter integration.
"""
from __future__ import annotations
from dataclasses import dataclass
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)
from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME


@dataclass
class Problem:
    severity: str  # "error" | "warning" | "info"
    message: str
    file_path: str
    line: int
    column: int = 0


class ProblemsPanel(QWidget):
    """Displays errors, warnings, and info messages."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._problems: list[Problem] = []
        self._build_ui()
        signals.problems_updated.connect(self.set_problems)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(28)
        toolbar.setStyleSheet(f"background: {THEME.bg_surface};")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(THEME.space_lg, 0, THEME.space_lg, 0)

        self._count_label = QLabel("No problems")
        self._count_label.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: {THEME.font_size_xs}px;"
            " background: transparent;"
        )
        tb_layout.addWidget(self._count_label)
        tb_layout.addStretch()
        layout.addWidget(toolbar)

        # Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet(
            f"QTreeWidget {{ background: {THEME.bg_inset}; color: {THEME.text_secondary};"
            f" border: none; font-size: {THEME.font_size_sm}px;"
            f" font-family: {THEME.font_mono}; }}"
            f"QTreeWidget::item {{ padding: {THEME.space_sm}px; }}"
            f"QTreeWidget::item:hover {{ background: {THEME.bg_hover}; }}"
            f"QTreeWidget::item:selected {{ background: {THEME.accent_muted}; }}"
        )
        self._tree.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree, stretch=1)

    def set_problems(self, problems: list[Problem]) -> None:
        self._problems = problems
        self._tree.clear()
        errors = sum(1 for p in problems if p.severity == "error")
        warnings = sum(1 for p in problems if p.severity == "warning")
        
        if errors == 0 and warnings == 0:
            self._count_label.setText("No problems")
        else:
            self._count_label.setText(f"{errors} errors, {warnings} warnings")

        for p in problems:
            icon = "\u2716" if p.severity == "error" else "\u26A0" if p.severity == "warning" else "\u2139"
            from pathlib import Path
            fname = Path(p.file_path).name
            text = f"{icon}  {p.message}  ({fname}:{p.line})"
            item = QTreeWidgetItem([text])
            item.setData(0, Qt.ItemDataRole.UserRole, p)
            self._tree.addTopLevelItem(item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        problem = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(problem, Problem):
            signals.file_open_requested.emit(problem.file_path)
            # Need to jump to line. We use a small delay to ensure the file opens before jumping.
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: signals.goto_line_requested.emit(problem.line, problem.column))

    def clear(self) -> None:
        self._problems = []
        self._tree.clear()
        self._count_label.setText("No problems")
