"""Document view widget.

Displays the content of an opened file.  Phase 1 uses a styled QPlainTextEdit.
Future phases will add syntax highlighting, line numbers, minimap, etc.
"""

from __future__ import annotations

from PyQt5.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from friday_ai.core.theme import THEME


class DocumentView(QWidget):
    """Styled text display for document content."""

    def __init__(self, content: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui(content)

    def _build_ui(self, content: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._editor = QPlainTextEdit()
        self._editor.setPlainText(content)
        self._editor.setReadOnly(True)
        self._editor.setStyleSheet(
            f"QPlainTextEdit {{"
            f"  background: {THEME.bg_base}; "
            f"  color: {THEME.text_primary}; "
            f"  font-family: {THEME.font_mono}; "
            f"  font-size: {THEME.font_size_base}px; "
            f"  border: none; "
            f"  padding: {THEME.space_xl}px; "
            f"  selection-background-color: {THEME.accent_muted}; "
            f"}}"
        )

        layout.addWidget(self._editor)

    def set_content(self, text: str) -> None:
        """Replace the displayed content."""
        self._editor.setPlainText(text)

    def content(self) -> str:
        """Return the current content."""
        return self._editor.toPlainText()
