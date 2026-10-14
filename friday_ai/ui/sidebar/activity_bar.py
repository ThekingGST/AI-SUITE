"""FRIDAY Activity Bar — the vertical icon strip on the far left.

Contains views (Explorer, Search, Outline) at the top, and
Workspace switchers (JARVIS, FRIDAY, EDITH) / Settings at the bottom.
"""

from __future__ import annotations

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME

_VIEWS = (
    ("explorer", "folder", "Explorer"),
    ("search", "search", "Search"),
    ("outline", "list", "Outline"),
)


class ActivityBar(QWidget):
    """Vertical icon strip for switching sidebar views and workspaces."""
    
    view_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activityBar")
        self.setFixedWidth(THEME.dock_width)
        
        self._view_buttons: dict[str, QPushButton] = {}
        self._active_view = "explorer"
        
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, THEME.space_md, 0, THEME.space_md)
        layout.setSpacing(THEME.space_sm)
        layout.setAlignment(Qt.AlignTop)

        # ── Views (Top) ──
        for view_id, icon_name, tooltip in _VIEWS:
            btn = QPushButton()
            btn.setIcon(Icons.get(icon_name, color=THEME.text_muted, size=24))
            btn.setIconSize(QSize(24, 24))
            btn.setFixedSize(THEME.dock_width, THEME.dock_width)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("view_id", view_id)
            btn.clicked.connect(lambda checked=False, v=view_id: self._on_view_click(v))
            self._apply_view_style(btn, view_id == self._active_view)
            self._view_buttons[view_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Settings (keep settings in FRIDAY, but remove workspace buttons to prevent duplication)
        settings_btn = QPushButton()
        settings_btn.setIcon(Icons.get("settings", color=THEME.text_muted, size=20))
        settings_btn.setIconSize(QSize(20, 20))
        settings_btn.setFixedSize(THEME.dock_width, THEME.dock_width)
        settings_btn.setToolTip("Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(lambda: signals.settings_requested.emit())
        # We need a new helper or reuse view style since _apply_ws_style is removed
        settings_btn.setStyleSheet(
            f"QPushButton {{ "
            f"  background: transparent; "
            f"  border: none; "
            f"  border-radius: 0; "
            f"}} "
            f"QPushButton:hover {{ background: {THEME.bg_hover}; }}"
        )
        layout.addWidget(settings_btn)

    def _on_view_click(self, view_id: str) -> None:
        if self._active_view == view_id:
            return
        self._active_view = view_id
        for vid, btn in self._view_buttons.items():
            self._apply_view_style(btn, vid == view_id)
        self.view_changed.emit(view_id)

    def _on_ws_click(self, ws_id: str) -> None:
        from friday_ai.core.signals import signals
        signals.workspace_switch_requested.emit(ws_id)

    def _apply_view_style(self, btn: QPushButton, active: bool) -> None:
        icon_map = {vid: icon for vid, icon, _ in _VIEWS}
        icon_name = icon_map.get(btn.property("view_id"), "help")
        color = THEME.text_primary if active else THEME.text_muted
        btn.setIcon(Icons.get(icon_name, color=color, size=24))
        
        if active:
            btn.setStyleSheet(
                f"QPushButton {{ "
                f"  background: transparent; "
                f"  border: none; "
                f"  border-left: 2px solid {THEME.accent}; "
                f"  border-radius: 0; "
                f"}} "
                f"QPushButton:hover {{ background: {THEME.bg_hover}; }}"
            )
        else:
            btn.setStyleSheet(
                f"QPushButton {{ "
                f"  background: transparent; "
                f"  border: none; "
                f"  border-left: 2px solid transparent; "
                f"  border-radius: 0; "
                f"}} "
                f"QPushButton:hover {{ background: {THEME.bg_hover}; }}"
        )
