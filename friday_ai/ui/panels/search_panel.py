"""Project search panel — search across all files."""
from __future__ import annotations
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)
from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from friday_ai.services.search_service import SearchService, SearchMatch


class SearchPanel(QWidget):
    """Project-wide search with results tree."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = SearchService(self)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._do_search)
        self._service.results_ready.connect(self._on_results)
        self._build_ui()
        signals.project_opened.connect(self._on_project_opened)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(THEME.space_xl, THEME.space_lg, THEME.space_md, THEME.space_lg)

        title = QLabel("SEARCH")
        title.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: {THEME.font_size_xs}px;"
            " font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        h_layout.addWidget(title)
        h_layout.addStretch()
        layout.addWidget(header)

        # Search input
        input_container = QWidget()
        input_container.setStyleSheet("background: transparent;")
        ic_layout = QVBoxLayout(input_container)
        ic_layout.setContentsMargins(THEME.space_lg, 0, THEME.space_lg, THEME.space_lg)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Search files...")
        self._input.setFixedHeight(30)
        self._input.setStyleSheet(
            f"QLineEdit {{ background: {THEME.bg_inset}; color: {THEME.text_primary};"
            f" border: {THEME.border_width}px solid {THEME.border_default};"
            f" border-radius: {THEME.radius_sm}px; padding: 0 {THEME.space_md}px;"
            f" font-size: {THEME.font_size_sm}px; }}"
            f"QLineEdit:focus {{ border-color: {THEME.accent}; }}"
        )
        self._input.textChanged.connect(lambda: self._debounce.start())
        ic_layout.addWidget(self._input)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(
            f"color: {THEME.text_muted}; font-size: {THEME.font_size_xs}px;"
            " background: transparent;"
        )
        ic_layout.addWidget(self._count_label)
        layout.addWidget(input_container)

        # Results tree
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet(
            f"QTreeWidget {{ background: transparent; color: {THEME.text_secondary};"
            f" border: none; font-size: {THEME.font_size_sm}px; }}"
            f"QTreeWidget::item {{ padding: {THEME.space_xs}px; }}"
            f"QTreeWidget::item:hover {{ background: {THEME.bg_hover}; }}"
            f"QTreeWidget::item:selected {{ background: {THEME.accent_muted}; }}"
        )
        self._tree.itemDoubleClicked.connect(self._on_item_clicked)
        layout.addWidget(self._tree, stretch=1)

    def _on_project_opened(self, path: str) -> None:
        self._service.set_project_root(path)

    def _do_search(self) -> None:
        query = self._input.text().strip()
        if not query:
            self._tree.clear()
            self._count_label.setText("")
            return
        self._count_label.setText("Searching...")
        self._service.search(query)

    def _on_results(self, matches: list) -> None:
        self._tree.clear()
        if not matches:
            self._count_label.setText("No results")
            return
        self._count_label.setText(f"{len(matches)} results")

        # Group by file
        by_file: dict[str, list] = {}
        for m in matches:
            by_file.setdefault(m.file_path, []).append(m)

        for file_path, file_matches in by_file.items():
            fname = Path(file_path).name
            file_item = QTreeWidgetItem([f"{fname} ({len(file_matches)})" ])
            file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            for m in file_matches:
                line_text = f"  L{m.line_number}: {m.line_content.strip()[:80]}"
                child = QTreeWidgetItem([line_text])
                child.setData(0, Qt.ItemDataRole.UserRole, m)
                file_item.addChild(child)
            self._tree.addTopLevelItem(file_item)
            file_item.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, SearchMatch):
            signals.file_open_requested.emit(data.file_path)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: signals.goto_line_requested.emit(data.line_number, 0))
        elif isinstance(data, str):
            signals.file_open_requested.emit(data)

    def focus_search(self) -> None:
        self._input.setFocus()
        self._input.selectAll()
