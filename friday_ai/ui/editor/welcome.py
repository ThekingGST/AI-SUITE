"""Welcome tab — FRIDAY's branded landing page.

Displayed when no project is open.  The "Open Project" button triggers a
folder picker dialog.  This is the first thing the user sees and sets the
tone for the entire application.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from friday_ai import __version__
from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME


class WelcomeTab(QWidget):
    """Branded landing page shown when no files are open."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("welcomePage")
        self._build_ui()

    def _build_ui(self) -> None:
        # Centre everything
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        container = QWidget()
        container.setMaximumWidth(480)
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(THEME.space_2xl)

        # ── Logo / Title ─────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignCenter)
        title_row.setSpacing(THEME.space_lg)

        logo = QLabel()
        logo.setPixmap(Icons.pixmap("code", color=THEME.accent, size=36))
        logo.setStyleSheet("background: transparent;")
        title_row.addWidget(logo)

        title = QLabel("FRIDAY")
        title.setStyleSheet(
            f"color: {THEME.text_primary}; "
            f"font-size: {THEME.font_size_title}px; "
            "font-weight: bold; "
            "background: transparent; "
            "letter-spacing: 2px;"
        )
        title_row.addWidget(title)
        layout.addLayout(title_row)

        # ── Subtitle ─────────────────────────────────────────────────────
        subtitle = QLabel("AI Software Engineer")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_lg}px; "
            "background: transparent;"
        )
        layout.addWidget(subtitle)

        # ── Version badge ────────────────────────────────────────────────
        version = QLabel(f"v{__version__}  \u2022  Phase 1: IDE Shell")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet(
            f"color: {THEME.text_muted}; "
            f"font-size: {THEME.font_size_sm}px; "
            "background: transparent;"
        )
        layout.addWidget(version)

        # ── Spacer ───────────────────────────────────────────────────────
        layout.addSpacing(THEME.space_3xl)

        # ── Action buttons ───────────────────────────────────────────────
        actions = QVBoxLayout()
        actions.setSpacing(THEME.space_lg)

        self._open_btn = self._make_action(
            "folder-open", "Open Project", THEME.accent,
        )
        self._open_btn.clicked.connect(self._on_open_project)
        actions.addWidget(self._open_btn)

        recent_btn = self._make_action(
            "files", "Recent Projects", THEME.text_secondary,
        )
        actions.addWidget(recent_btn)

        layout.addLayout(actions)

        # ── Spacer ───────────────────────────────────────────────────────
        layout.addSpacing(THEME.space_3xl)

        # ── Keyboard hints ───────────────────────────────────────────────
        hints = QLabel(
            "Ctrl+O  Open Project   \u2022   "
            "Ctrl+P  Command Palette   \u2022   "
            "Ctrl+`  Mission Control"
        )
        hints.setAlignment(Qt.AlignCenter)
        hints.setWordWrap(True)
        hints.setStyleSheet(
            f"color: {THEME.text_muted}; "
            f"font-size: {THEME.font_size_xs}px; "
            "background: transparent;"
        )
        layout.addWidget(hints)

        outer.addWidget(container)

    def _make_action(self, icon_name: str, text: str, color: str) -> QPushButton:
        btn = QPushButton(f"  {text}")
        btn.setIcon(Icons.get(icon_name, color=color, size=18))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(42)
        btn.setStyleSheet(
            f"QPushButton {{ "
            f"  background: {THEME.bg_overlay}; "
            f"  color: {THEME.text_primary}; "
            f"  border: {THEME.border_width}px solid {THEME.border_default}; "
            f"  border-radius: {THEME.radius_lg}px; "
            f"  padding: 0 {THEME.space_2xl}px; "
            f"  font-size: {THEME.font_size_base}px; "
            f"  text-align: left; "
            f"}} "
            f"QPushButton:hover {{ "
            f"  background: {THEME.bg_hover}; "
            f"  border-color: {THEME.accent}; "
            f"}}"
        )
        return btn

    # ── Actions ──────────────────────────────────────────────────────────

    def _on_open_project(self) -> None:
        """Open a native folder picker and request project loading."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Open Project",
            "",
            QFileDialog.ShowDirsOnly,
        )
        if path:
            signals.project_open_requested.emit(path)
