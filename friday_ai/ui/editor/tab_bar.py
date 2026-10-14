"""Custom tab bar for the editor area.

Each tab represents an open document.  Tabs support close buttons, hover
effects, and an active state indicator.  The tab bar emits signals through
the application event bus.
"""

from __future__ import annotations

from PyQt5.QtCore import QSize, Qt, pyqtSignal as Signal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from friday_ai.core.icons import Icons
from friday_ai.core.theme import THEME


class _TabButton(QWidget):
    """A single tab in the bar."""

    clicked = Signal()
    close_clicked = Signal()

    def __init__(
        self,
        title: str,
        icon_name: str = "file-text",
        closable: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(THEME.tab_height)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            THEME.space_lg, 0, THEME.space_md if closable else THEME.space_lg, 0,
        )
        layout.setSpacing(THEME.space_md)

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(Icons.pixmap(icon_name, color=THEME.text_muted, size=14))
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)

        # Title
        self._label = QLabel(title)
        self._label.setStyleSheet(
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_sm}px; "
            "background: transparent;"
        )
        layout.addWidget(self._label)

        # Close button
        if closable:
            close_btn = QPushButton()
            close_btn.setIcon(Icons.get("close", color=THEME.text_muted, size=12))
            close_btn.setIconSize(QSize(12, 12))
            close_btn.setFixedSize(18, 18)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; border-radius: {THEME.radius_sm}px; }}"
                f"QPushButton:hover {{ background: {THEME.bg_active}; }}"
            )
            close_btn.clicked.connect(self.close_clicked.emit)
            layout.addWidget(close_btn)

        self._update_style()

    @property
    def title(self) -> str:
        return self._title

    def set_title(self, title: str) -> None:
        """Update the displayed title."""
        self._title = title
        self._label.setText(title)

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value
        self._update_style()

    def _update_style(self) -> None:
        if self._active:
            self.setStyleSheet(
                f"background: {THEME.bg_base}; "
                f"border-bottom: 2px solid {THEME.accent};"
            )
            self._label.setStyleSheet(
                f"color: {THEME.text_primary}; "
                f"font-size: {THEME.font_size_sm}px; "
                "background: transparent;"
            )
        else:
            self.setStyleSheet(
                f"background: {THEME.bg_surface}; "
                "border-bottom: 2px solid transparent;"
            )
            self._label.setStyleSheet(
                f"color: {THEME.text_secondary}; "
                f"font-size: {THEME.font_size_sm}px; "
                "background: transparent;"
            )

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class TabBar(QWidget):
    """Horizontal tab bar with closable tabs."""

    tab_selected = Signal(int)
    tab_closed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tabBar")
        self.setFixedHeight(THEME.tab_height)
        self._tabs: list[_TabButton] = []
        self._active_index = -1

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.setAlignment(Qt.AlignLeft)

    def add_tab(
        self,
        title: str,
        *,
        icon_name: str = "file-text",
        closable: bool = True,
    ) -> int:
        """Add a new tab and return its index."""
        tab = _TabButton(title, icon_name=icon_name, closable=closable)
        index = len(self._tabs)
        tab.clicked.connect(lambda idx=index: self.select(idx))
        tab.close_clicked.connect(lambda idx=index: self._close(idx))
        self._tabs.append(tab)
        self._layout.addWidget(tab)
        self.select(index)
        return index

    def select(self, index: int) -> None:
        """Activate the tab at *index*."""
        if index < 0 or index >= len(self._tabs):
            return
        for i, tab in enumerate(self._tabs):
            tab.active = (i == index)
        self._active_index = index
        self.tab_selected.emit(index)

    def _close(self, index: int) -> None:
        """Close the tab at *index*."""
        if index < 0 or index >= len(self._tabs):
            return
        tab = self._tabs.pop(index)
        self._layout.removeWidget(tab)
        tab.deleteLater()

        # Re-bind click handlers with updated indices
        for i, t in enumerate(self._tabs):
            t.clicked.disconnect()
            t.close_clicked.disconnect()
            t.clicked.connect(lambda checked=False, idx=i: self.select(idx))
            t.close_clicked.connect(lambda checked=False, idx=i: self._close(idx))

        self.tab_closed.emit(index)

        # Select the nearest remaining tab
        if self._tabs:
            new_index = min(index, len(self._tabs) - 1)
            self.select(new_index)
        else:
            self._active_index = -1

    def set_tab_title(self, index: int, title: str) -> None:
        """Update the title of the tab at *index*."""
        if 0 <= index < len(self._tabs):
            self._tabs[index].set_title(title)

    @property
    def count(self) -> int:
        return len(self._tabs)

    @property
    def active_index(self) -> int:
        return self._active_index
