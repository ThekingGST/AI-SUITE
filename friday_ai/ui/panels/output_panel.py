"""Output panel — displays run output, system messages, etc."""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor, QKeySequence
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QVBoxLayout, QWidget, QApplication
)
from friday_ai.core.icons import Icons
from friday_ai.core.theme import THEME
from friday_ai.core.signals import signals


class OutputPanel(QWidget):
    """Scrollable output log with category filtering."""

    _COLORS = {
        "build": THEME.warning,
        "python": "#3572A5",
        "java": "#b07219",
        "c/c++": "#f34b7d",
        "node": "#f1e05a",
        "system": THEME.text_muted,
        "terminal": THEME.success,
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        signals.run_compile_started.connect(lambda f: self.append(f"Starting run pipeline for {f}\n", "system"))

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
        tb_layout.setSpacing(THEME.space_md)

        title = QLabel("Output")
        title.setStyleSheet(
            f"color: {THEME.text_secondary}; font-size: {THEME.font_size_xs}px;"
            " font-weight: bold; background: transparent;"
        )
        tb_layout.addWidget(title)
        tb_layout.addStretch()

        self._explain_btn = QPushButton("Explain Error")
        self._explain_btn.setFixedHeight(22)
        self._explain_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_btn(self._explain_btn)
        self._explain_btn.setStyleSheet(
            f"QPushButton {{ background: {THEME.danger}; color: {THEME.bg_base};"
            f" border: none; font-size: {THEME.font_size_xs}px;"
            f" padding: 0 {THEME.space_md}px; border-radius: {THEME.radius_sm}px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: #EF4444; }}"
        )
        self._explain_btn.hide()
        self._explain_btn.clicked.connect(self._on_explain)
        tb_layout.addWidget(self._explain_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedHeight(22)
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_btn(self._stop_btn)
        self._stop_btn.clicked.connect(lambda: signals.run_stop_requested.emit())
        tb_layout.addWidget(self._stop_btn)

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedHeight(22)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_btn(copy_btn)
        copy_btn.clicked.connect(self._copy_all)
        tb_layout.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(22)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_btn(clear_btn)
        clear_btn.clicked.connect(self.clear)
        tb_layout.addWidget(clear_btn)

        layout.addWidget(toolbar)

        # Log area
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        font = QFont(THEME.font_mono)
        font.setPixelSize(THEME.font_size_sm)
        self._log.setFont(font)
        self._log.setStyleSheet(
            f"QPlainTextEdit {{ background: {THEME.bg_inset}; color: {THEME.text_secondary};"
            f" border: none; padding: {THEME.space_md}px; }}"
        )
        self._log.setMaximumBlockCount(5000)
        layout.addWidget(self._log, stretch=1)

    def _style_btn(self, btn: QPushButton) -> None:
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {THEME.text_muted};"
            f" border: none; font-size: {THEME.font_size_xs}px;"
            f" padding: 0 {THEME.space_md}px; border-radius: {THEME.radius_sm}px; }}"
            f"QPushButton:hover {{ background: {THEME.bg_hover}; color: {THEME.text_secondary}; }}"
        )

    def append(self, text: str, category: str = "system") -> None:
        """Append text to the output log with colors."""
        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = QTextCharFormat()
        color = self._COLORS.get(category, THEME.text_secondary)
        fmt.setForeground(QColor(color))
        
        cursor.insertText(text, fmt)
        self._log.setTextCursor(cursor)
        self._log.ensureCursorVisible()

    def clear(self) -> None:
        self._log.clear()

    def _copy_all(self) -> None:
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self._log.toPlainText())
            
    def show_explain_button(self, friendly_msg: str, raw_stderr: str) -> None:
        """Show the explain button with context."""
        self._last_error_context = raw_stderr
        self._explain_btn.show()
        
    def _on_explain(self) -> None:
        """User clicked Explain Error."""
        self._explain_btn.hide()
        context = getattr(self, "_last_error_context", "")
        prompt = f"Explain this error and how to fix it:\n\n```\n{context}\n```"
        signals.ai_prompt_submitted.emit(prompt, "explain")
