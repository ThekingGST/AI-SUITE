"""Outline panel — displays classes, functions, methods for Python files."""
from __future__ import annotations
import ast
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)
from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME


class OutlinePanel(QWidget):
    """Displays code structure for the current file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_file: str = ""
        self._build_ui()
        signals.file_opened.connect(self._on_file_opened)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(THEME.space_xl, THEME.space_lg, THEME.space_md, THEME.space_lg)

        title = QLabel("OUTLINE")
        title.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: {THEME.font_size_xs}px;"
            " font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        h_layout.addWidget(title)
        h_layout.addStretch()
        layout.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet(
            f"QTreeWidget {{ background: transparent; color: {THEME.text_secondary};"
            f" border: none; font-size: {THEME.font_size_sm}px; }}"
            f"QTreeWidget::item {{ padding: {THEME.space_xs}px; }}"
            f"QTreeWidget::item:hover {{ background: {THEME.bg_hover}; }}"
            f"QTreeWidget::item:selected {{ background: {THEME.accent_muted}; }}"
        )
        layout.addWidget(self._tree, stretch=1)

        self._placeholder = QLabel("Open a Python file to see outline")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: {THEME.font_size_sm}px;"
            " background: transparent;"
        )
        layout.addWidget(self._placeholder)
        self._tree.hide()

    def _on_file_opened(self, path: str) -> None:
        self._current_file = path
        if Path(path).suffix.lower() in (".py", ".pyw"):
            self._parse_python(path)
        else:
            self._tree.clear()
            self._tree.hide()
            self._placeholder.setText(f"Outline not available for {Path(path).suffix} files")
            self._placeholder.show()

    def _parse_python(self, path: str) -> None:
        try:
            source = Path(path).read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (SyntaxError, OSError):
            self._tree.clear()
            self._placeholder.setText("Could not parse file")
            self._placeholder.show()
            self._tree.hide()
            return

        self._tree.clear()
        self._placeholder.hide()
        self._tree.show()

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_item = QTreeWidgetItem([f"\u25C6 {node.name}"])
                class_item.setData(0, Qt.ItemDataRole.UserRole, node.lineno)
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                        prefix = "\u25CB" if child.name.startswith("_") else "\u25CF"
                        method = QTreeWidgetItem([f"  {prefix} {child.name}()"])
                        method.setData(0, Qt.ItemDataRole.UserRole, child.lineno)
                        class_item.addChild(method)
                self._tree.addTopLevelItem(class_item)
                class_item.setExpanded(True)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                fn_item = QTreeWidgetItem([f"\u0192 {node.name}()"])
                fn_item.setData(0, Qt.ItemDataRole.UserRole, node.lineno)
                self._tree.addTopLevelItem(fn_item)

        self._tree.itemDoubleClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        line = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(line, int) and self._current_file:
            signals.file_open_requested.emit(self._current_file)
