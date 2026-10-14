"""AI Suite dock — the vertical icon strip on the far left.

Switches between JARVIS, FRIDAY, and EDITH workspaces.  Each icon is a
clickable button with hover and active states.  The active workspace is
highlighted with the accent colour.
"""

from __future__ import annotations

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME


_WORKSPACES = (
    ("jarvis", "robot", "JARVIS — Personal Assistant"),
    ("friday", "code", "FRIDAY — Software Engineer"),
    ("edith", "flask", "EDITH — Research Assistant"),
)


class SuiteDock(QWidget):
    """Vertical icon strip for switching AI workspaces."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("suiteDock")
        self.setFixedWidth(THEME.dock_width)
        self._buttons: dict[str, QPushButton] = {}
        self._active = "friday"
        self._build_ui()

    # ── Construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, THEME.space_md, 0, THEME.space_md)
        layout.setSpacing(THEME.space_sm)
        layout.setAlignment(Qt.AlignTop)

        for ws_id, icon_name, tooltip in _WORKSPACES:
            btn = QPushButton()
            btn.setIcon(Icons.get(icon_name, color=THEME.text_muted, size=22))
            btn.setIconSize(QSize(22, 22))
            btn.setFixedSize(THEME.dock_width, THEME.dock_width)
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("ws_id", ws_id)
            btn.clicked.connect(lambda checked=False, w=ws_id: self._on_click(w))
            self._apply_style(btn, ws_id == self._active)
            self._buttons[ws_id] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Bottom: settings
        settings_btn = QPushButton()
        settings_btn.setIcon(Icons.get("settings", color=THEME.text_muted, size=20))
        settings_btn.setIconSize(QSize(20, 20))
        settings_btn.setFixedSize(THEME.dock_width, THEME.dock_width)
        settings_btn.setToolTip("Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(settings_btn, False)
        layout.addWidget(settings_btn)

    # ── Styling ──────────────────────────────────────────────────────────

    def _apply_style(self, btn: QPushButton, active: bool) -> None:
        if active:
            btn.setIcon(
                Icons.get(
                    btn.property("ws_id") or "settings",
                    color=THEME.text_primary,
                    size=22 if btn.property("ws_id") else 20,
                )
            )
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

    # ── Click handling ───────────────────────────────────────────────────

    def _on_click(self, ws_id: str) -> None:
        if ws_id == self._active:
            return
        # Deactivate previous
        old_btn = self._buttons.get(self._active)
        if old_btn:
            old_icon = next(
                name for wid, name, _ in _WORKSPACES if wid == self._active
            )
            old_btn.setIcon(Icons.get(old_icon, color=THEME.text_muted, size=22))
            self._apply_style(old_btn, False)

        # Activate new
        self._active = ws_id
        new_btn = self._buttons[ws_id]
        new_icon = next(name for wid, name, _ in _WORKSPACES if wid == ws_id)
        new_btn.setIcon(Icons.get(new_icon, color=THEME.text_primary, size=22))
        self._apply_style(new_btn, True)

        signals.workspace_switched.emit(ws_id)
