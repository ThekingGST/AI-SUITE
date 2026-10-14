"""Sidebar container — combines the Activity Bar and Sidebar Views (Explorer, Search, Outline)."""

from __future__ import annotations

from PyQt5.QtWidgets import QHBoxLayout, QWidget, QStackedWidget

from friday_ai.core.theme import THEME
from friday_ai.ui.sidebar.explorer import FileExplorer
from friday_ai.ui.sidebar.activity_bar import ActivityBar
from friday_ai.ui.panels.search_panel import SearchPanel
from friday_ai.ui.panels.outline_panel import OutlinePanel


class SidebarPanel(QWidget):
    """Left sidebar: activity bar + stacked views."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarPanel")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Activity Bar (Far Left)
        self.activity_bar = ActivityBar()
        layout.addWidget(self.activity_bar)

        # 2. View Stack (Explorer, Search, Outline)
        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        self.explorer = FileExplorer()
        self.search = SearchPanel()
        self.outline = OutlinePanel()

        self._stack.addWidget(self.explorer) # index 0
        self._stack.addWidget(self.search)   # index 1
        self._stack.addWidget(self.outline)  # index 2

        # Connect activity bar switching
        self.activity_bar.view_changed.connect(self._on_view_changed)

    def _on_view_changed(self, view_id: str) -> None:
        if view_id == "explorer":
            self._stack.setCurrentIndex(0)
        elif view_id == "search":
            self._stack.setCurrentIndex(1)
        elif view_id == "outline":
            self._stack.setCurrentIndex(2)

    def show_search(self) -> None:
        self.activity_bar._on_view_click("search")

    def show_outline(self) -> None:
        self.activity_bar._on_view_click("outline")
