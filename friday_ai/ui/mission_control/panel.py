"""FRIDAY Mission Control panel.

This is NOT a terminal.  It is FRIDAY's brain activity display — showing
what the AI is currently doing: planning, reading, editing, testing, etc.

Phase 1: displays a static activity log.  Future phases will show real-time
AI pipeline state with animated phase indicators.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME


class MissionControlPanel(QWidget):
    """Bottom panel showing FRIDAY's current brain activity."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("missionControl")
        self._build_ui()
        self._connect_signals()
        self._show_idle()

    # ── Construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            THEME.space_xl, THEME.space_md, THEME.space_xl, THEME.space_md,
        )
        layout.setSpacing(THEME.space_md)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(THEME.space_md)

        icon_label = QLabel()
        icon_label.setPixmap(Icons.pixmap("activity", color=THEME.text_secondary, size=14))
        header.addWidget(icon_label)

        title = QLabel("MISSION CONTROL")
        title.setStyleSheet(
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_xs}px; "
            "font-weight: bold; "
            "letter-spacing: 1px; "
            "background: transparent;"
        )
        header.addWidget(title)

        # Phase indicator
        self._phase_label = QLabel()
        self._phase_label.setStyleSheet(
            f"color: {THEME.accent}; "
            f"font-size: {THEME.font_size_xs}px; "
            "font-weight: bold; "
            "background: transparent;"
        )
        header.addStretch()
        header.addWidget(self._phase_label)

        layout.addLayout(header)

        # Activity log
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            f"background: {THEME.bg_inset}; "
            f"color: {THEME.text_secondary}; "
            f"font-family: {THEME.font_mono}; "
            f"font-size: {THEME.font_size_sm}px; "
            f"border: {THEME.border_width}px solid {THEME.border_muted}; "
            f"border-radius: {THEME.radius_md}px; "
            f"padding: {THEME.space_md}px;"
        )
        self._log.setMaximumBlockCount(200)
        layout.addWidget(self._log)

    # ── Signal handling ──────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        signals.mission_update.connect(self._on_update)
        signals.mission_clear.connect(self._on_clear)

    def _on_update(self, phase: str, message: str) -> None:
        self._phase_label.setText(phase.upper())
        self._log.appendPlainText(f"  {phase}  {message}")

    def _on_clear(self) -> None:
        self._log.clear()
        self._show_idle()

    def _show_idle(self) -> None:
        self._phase_label.setText("IDLE")
        self._log.setPlainText("  \u25cf  Ready \u2014 Waiting for instructions.")

    # ── Public API ───────────────────────────────────────────────────────

    def log(self, phase: str, message: str) -> None:
        """Programmatically add a mission log entry."""
        signals.mission_update.emit(phase, message)
