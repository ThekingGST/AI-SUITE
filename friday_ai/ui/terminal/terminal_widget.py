"""Terminal widget — interactive shell session in the IDE.

A styled QPlainTextEdit that interacts with a TerminalSession (QProcess).
Supports input, output, ANSI stripping, clear, and kill.
"""
from __future__ import annotations
import re
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import QPlainTextEdit, QWidget
from friday_ai.core.theme import THEME
from friday_ai.services.terminal_service import TerminalSession
from shared.logger import get_logger

LOG = get_logger("friday.terminal.widget")

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[^\[]")  


class TerminalWidget(QPlainTextEdit):
    """Interactive terminal widget backed by a shell process."""

    def __init__(
        self,
        shell_path: str,
        cwd: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = TerminalSession(shell_path, cwd, parent=self)
        self._input_start = 0
        self._setup_ui()
        self._session.output_received.connect(self._on_output)
        self._session.finished.connect(self._on_finished)
        self._session.start()

    def _setup_ui(self) -> None:
        font = QFont(THEME.font_mono)
        font.setPixelSize(THEME.font_size_base)
        self.setFont(font)
        self.setStyleSheet(
            f"QPlainTextEdit {{"
            f"  background: {THEME.bg_inset};"
            f"  color: {THEME.text_primary};"
            f"  border: none;"
            f"  selection-background-color: {THEME.accent_muted};"
            f"}}"
        )
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setUndoRedoEnabled(False)

    def _on_output(self, text: str) -> None:
        cleaned = _ANSI_ESCAPE.sub("", text)
        # Remove carriage returns for cleaner display
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "")
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(cleaned)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self._input_start = self.textCursor().position()

    def _on_finished(self, exit_code: int) -> None:
        self.appendPlainText(f"\n[Process exited with code {exit_code}]")
        self._input_start = self.textCursor().position()

    def keyPressEvent(self, event) -> None:
        cursor = self.textCursor()
        # Prevent editing output area
        if cursor.position() < self._input_start:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # Send the input line to the process
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            text = self.toPlainText()[self._input_start:]
            self._session.write(text)
            self.appendPlainText("")  # Move to new line
            self._input_start = self.textCursor().position()
            return

        if event.key() == Qt.Key.Key_Backspace:
            if cursor.position() <= self._input_start:
                return  # Don't delete prompt

        if event.key() == Qt.Key.Key_C and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if not self.textCursor().hasSelection():
                # Send Ctrl+C to process
                self._session.write("\x03")
                return

        super().keyPressEvent(event)

    def clear_terminal(self) -> None:
        self.clear()
        self._input_start = 0

    def kill_process(self) -> None:
        self._session.kill()

    def is_running(self) -> bool:
        return self._session.is_running()

    def restart(self, cwd: str = "") -> None:
        self._session.kill()
        self.clear()
        self._input_start = 0
        if cwd:
            self._session._cwd = cwd
        self._session.start()
