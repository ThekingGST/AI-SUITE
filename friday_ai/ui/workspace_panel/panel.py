"""FRIDAY Workspace Panel (right sidebar).

This is FRIDAY's home — the primary surface where the AI communicates with
the developer. It provides a dedicated chat interface, free of explorer clutter.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from friday_ai.ui.workspace_panel.chat_message import ChatMessageWidget
from friday_ai.ui.workspace_panel.model_selector import ModelSelector
from friday_ai.services.provider_manager import ProviderManager
from shared.logger import get_logger

LOG = get_logger("friday.workspace_panel")


class WorkspacePanel(QWidget):
    """Right sidebar — FRIDAY's dedicated interaction surface."""

    def __init__(self, provider_manager: ProviderManager = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workspacePanel")
        self.pm = provider_manager
        self._current_message: ChatMessageWidget | None = None
        self._build_ui()
        self._connect_signals()

    # ── Construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ───────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(
            f"background: {THEME.bg_surface}; "
            f"border-bottom: {THEME.border_width}px solid {THEME.border_muted};"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(
            THEME.space_xl, THEME.space_lg, THEME.space_xl, THEME.space_lg,
        )

        icon_label = QLabel()
        icon_label.setPixmap(Icons.pixmap("code", color=THEME.accent, size=16))
        header_layout.addWidget(icon_label)

        self._title = QLabel("FRIDAY Assistant")
        self._title.setStyleSheet(
            f"color: {THEME.text_primary}; "
            f"font-size: {THEME.font_size_base}px; "
            "font-weight: bold; "
            "background: transparent; "
            f"margin-left: {THEME.space_md}px;"
        )
        header_layout.addWidget(self._title)
        header_layout.addStretch()

        layout.addWidget(header)

        # ── Chat area (scrollable) ───────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )

        chat_container = QWidget()
        self._chat_layout = QVBoxLayout(chat_container)
        self._chat_layout.setContentsMargins(
            THEME.space_xl, THEME.space_xl, THEME.space_xl, THEME.space_xl,
        )
        self._chat_layout.setSpacing(THEME.space_lg)
        self._chat_layout.setAlignment(Qt.AlignTop)

        # Welcome message
        welcome = self._make_message(
            "friday",
            "Ready to assist. Open a project to get started, or ask me anything.",
        )
        self._chat_layout.addWidget(welcome)

        self._scroll.setWidget(chat_container)
        layout.addWidget(self._scroll, stretch=1)

        # ── Input area ───────────────────────────────────────────────────
        input_container = QWidget()
        
        # Model selector & Stop button row
        top_input_layout = QHBoxLayout()
        top_input_layout.setContentsMargins(0, 0, 0, 0)
        top_input_layout.setSpacing(THEME.space_sm)
        
        if self.pm:
            self._model_selector = ModelSelector(self.pm)
            top_input_layout.addWidget(self._model_selector, stretch=1)
            
        self._btn_stop = QLabel("Stop")
        self._btn_stop.setStyleSheet(f"color: #F87171; font-size: {THEME.font_size_sm}px; font-weight: bold; background: transparent;")
        self._btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_stop.mousePressEvent = lambda e: signals.ai_stop_requested.emit()
        self._btn_stop.hide()
        top_input_layout.addWidget(self._btn_stop)
        
        # Actions row
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(THEME.space_sm)
        
        for action in ["Explain", "Refactor", "Generate", "Debug", "Fix", "Optimize"]:
            btn = QLabel(action)
            btn.setStyleSheet(f"color: {THEME.text_secondary}; font-size: {THEME.font_size_xs}px; background: {THEME.bg_base}; padding: 2px 8px; border-radius: {THEME.radius_sm}px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Use default arguments for lambda binding in a loop
            btn.mousePressEvent = lambda e, a=action: self._on_action(a.lower())
            actions_layout.addWidget(btn)
        actions_layout.addStretch()
        
        input_layout_v = QVBoxLayout(input_container)
        input_layout_v.setContentsMargins(
            THEME.space_xl, THEME.space_lg, THEME.space_xl, THEME.space_lg,
        )
        input_layout_v.setSpacing(THEME.space_md)
        input_layout_v.addLayout(top_input_layout)
        
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask FRIDAY...")
        self._input.setStyleSheet(
            f"background: {THEME.bg_inset}; "
            f"color: {THEME.text_primary}; "
            f"border: {THEME.border_width}px solid {THEME.border_default}; "
            f"border-radius: {THEME.radius_lg}px; "
            f"padding: {THEME.space_md}px {THEME.space_xl}px; "
            f"font-size: {THEME.font_size_base}px;"
        )
        self._input.returnPressed.connect(self._on_send)
        input_layout_v.addWidget(self._input)
        input_layout_v.addLayout(actions_layout)

        layout.addWidget(input_container)

    # ── Signals ──────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        signals.ai_chunk_received.connect(self._on_chunk)
        signals.ai_response_complete.connect(self._on_complete)
        signals.ai_error.connect(self._on_error)
        signals.ai_busy.connect(self._on_busy)

    def _on_chunk(self, text: str) -> None:
        if not self._current_message:
            LOG.info("WorkspacePanel._on_chunk(): First chunk received, creating assistant message widget.")
            self._current_message = self._make_message("friday", "")
            self._chat_layout.addWidget(self._current_message)
            
        LOG.debug("WorkspacePanel._on_chunk(): Forwarding chunk to ChatMessageWidget.")
        try:
            self._current_message.append_chunk(text)
        except Exception as e:
            LOG.error("WorkspacePanel._on_chunk(): Exception when appending chunk: %s", e)
            
        self._scroll_to_bottom()

    def _on_complete(self, _text: str) -> None:
        LOG.info("WorkspacePanel._on_complete(): Stream completed.")
        self._current_message = None

    def _on_error(self, err: str) -> None:
        if self._current_message:
            self._current_message.append_chunk(f"\n\n**Error**: {err}")
            self._current_message = None
        else:
            msg = self._make_message("error", f"**Error**: {err}")
            self._chat_layout.addWidget(msg)
        self._scroll_to_bottom()

    def _on_busy(self, busy: bool) -> None:
        if busy:
            self._btn_stop.show()
            self._input.setEnabled(False)
        else:
            self._btn_stop.hide()
            self._input.setEnabled(True)
            self._input.setFocus()

    def _scroll_to_bottom(self) -> None:
        def do_scroll():
            self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())
        QTimer.singleShot(10, do_scroll)

    # ── Message rendering ────────────────────────────────────────────────

    @staticmethod
    def _make_message(role: str, text: str) -> QWidget:
        """Create a styled message bubble."""
        return ChatMessageWidget(role, text)

    # ── Input handling ───────────────────────────────────────────────────

    def _on_action(self, action: str) -> None:
        text = self._input.text().strip()
        self._submit(text, action)
        
    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._submit(text, "")

    def _submit(self, prompt: str, action: str) -> None:
        display_text = prompt
        if action and not prompt:
            display_text = f"*{action.title()}*"
        elif action and prompt:
            display_text = f"*{action.title()}*: {prompt}"
            
        if not display_text:
            return
            
        self._input.clear()
        user_msg = self._make_message("user", display_text)
        self._chat_layout.addWidget(user_msg)
        self._scroll_to_bottom()
        
        self._current_message = None
        signals.ai_prompt_submitted.emit(prompt, action)
