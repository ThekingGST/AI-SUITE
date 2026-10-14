"""Production code editor widget.

Replaces the Phase 1 ``DocumentView`` with a fully functional code editor
featuring:

    * Line numbers with gutter
    * Current-line highlight
    * Syntax highlighting (via highlighter module)
    * Search (Ctrl+F) and Replace (Ctrl+H)
    * Undo / Redo (built into QPlainTextEdit)
    * Zoom (Ctrl+= / Ctrl+-)
    * Auto-indentation
    * Bracket matching
    * Cursor position reporting via signals
    * Dirty state tracking
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QRect, QSize, Qt, pyqtSignal as Signal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QTextCursor,
    QTextFormat,
)
from PyQt5.QtWidgets import (
    QAction,
    QShortcut,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from friday_ai.ui.editor.highlighter import get_highlighter, get_file_type, get_line_ending


# ── Bracket matching pairs ───────────────────────────────────────────────
_OPEN_BRACKETS = {"(": ")", "[": "]", "{": "}"}
_CLOSE_BRACKETS = {")": "(", "]": "[", "}": "{"}
_ALL_BRACKETS = set(_OPEN_BRACKETS) | set(_CLOSE_BRACKETS)


class _LineNumberArea(QWidget):
    """Gutter widget that draws line numbers alongside the editor."""

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Full-featured code editor with line numbers and syntax highlighting.

    Signals
    -------
    dirty_changed(bool)
        Emitted when the dirty state changes.
    """

    dirty_changed = Signal(bool)

    def __init__(
        self,
        content: str = "",
        file_path: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._file_path = file_path
        self._dirty = False
        self._original_content = content
        self._zoom_level = 0
        self._base_font_size = THEME.font_size_base

        self._setup_editor()
        self._setup_line_numbers()
        self._setup_highlighter()

        if content:
            self.setPlainText(content)
            self._dirty = False  # Reset after setPlainText

        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_moved)

    # ── Setup ────────────────────────────────────────────────────────────

    def _setup_editor(self) -> None:
        font = QFont(THEME.font_mono)
        font.setPixelSize(self._base_font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance(" ") * 4,
        )
        self.setStyleSheet(
            f"QPlainTextEdit {{"
            f"  background: {THEME.bg_base}; "
            f"  color: {THEME.text_primary}; "
            f"  border: none; "
            f"  selection-background-color: {THEME.accent_muted}; "
            f"}}"
        )
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def _setup_line_numbers(self) -> None:
        self._line_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self._update_line_area_width()

    def _setup_highlighter(self) -> None:
        self._highlighter = None
        if self._file_path:
            ext = Path(self._file_path).suffix
            self._highlighter = get_highlighter(ext, self.document())

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def dirty(self) -> bool:
        return self._dirty

    @dirty.setter
    def dirty(self, value: bool) -> None:
        if self._dirty != value:
            self._dirty = value
            self.dirty_changed.emit(value)

    @property
    def file_type(self) -> str:
        if self._file_path:
            return get_file_type(Path(self._file_path).suffix)
        return "Plain Text"

    @property
    def line_ending(self) -> str:
        return get_line_ending(self._original_content)

    # ── Line numbers ─────────────────────────────────────────────────────

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        space = THEME.space_xl + self.fontMetrics().horizontalAdvance("9") * digits + THEME.space_lg
        return space

    def _update_line_area_width(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()),
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor(THEME.bg_surface))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        current_line = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_line:
                    painter.setPen(QColor(THEME.text_primary))
                else:
                    painter.setPen(QColor(THEME.text_muted))
                painter.drawText(
                    0, top,
                    self._line_area.width() - THEME.space_md, self.fontMetrics().height(),
                    Qt.AlignRight, number,
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1
        painter.end()

    # ── Current line highlight ───────────────────────────────────────────

    def _on_cursor_moved(self) -> None:
        # Highlight current line
        selections = []
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor(THEME.bg_hover))
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        selections.append(sel)

        # Bracket matching
        selections.extend(self._bracket_matches())

        self.setExtraSelections(selections)

        # Report cursor position
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        signals.cursor_position.emit(line, col)

        if cursor.hasSelection():
            signals.selection_changed.emit(cursor.selectedText())
        else:
            signals.selection_changed.emit("")

    # ── Bracket matching ─────────────────────────────────────────────────

    def _bracket_matches(self) -> list:
        selections = []
        cursor = self.textCursor()
        block = cursor.block()
        text = block.text()
        pos_in_block = cursor.positionInBlock()

        # Check character at and before cursor
        for offset in (0, -1):
            check_pos = pos_in_block + offset
            if check_pos < 0 or check_pos >= len(text):
                continue
            char = text[check_pos]
            if char not in _ALL_BRACKETS:
                continue

            match_pos = self._find_matching_bracket(
                cursor.position() + offset, char,
            )
            if match_pos is not None:
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(THEME.accent_muted))
                fmt.setForeground(QColor(THEME.accent))
                for p in (cursor.position() + offset, match_pos):
                    sel = QTextEdit.ExtraSelection()
                    sel.format = fmt
                    c = QTextCursor(self.document())
                    c.setPosition(p)
                    c.movePosition(QTextCursor.Right, QTextCursor.MoveMode.KeepAnchor)
                    sel.cursor = c
                    selections.append(sel)
                break
        return selections

    def _find_matching_bracket(self, pos: int, char: str) -> int | None:
        doc = self.document()
        if char in _OPEN_BRACKETS:
            target = _OPEN_BRACKETS[char]
            direction = 1
        elif char in _CLOSE_BRACKETS:
            target = _CLOSE_BRACKETS[char]
            direction = -1
        else:
            return None

        depth = 0
        i = pos
        while 0 <= i < doc.characterCount():
            c = doc.characterAt(i)
            if c == char:
                depth += 1
            elif c == target:
                depth -= 1
                if depth == 0:
                    return i
            i += direction
        return None

    # ── Dirty tracking ───────────────────────────────────────────────────

    def _on_text_changed(self) -> None:
        self.dirty = self.toPlainText() != self._original_content

    def mark_saved(self) -> None:
        """Mark the document as saved (resets dirty state)."""
        self._original_content = self.toPlainText()
        self.dirty = False

    # ── Auto-indentation ─────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self._handle_auto_indent()
            return

        # Zoom
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Equal or event.key() == Qt.Key.Key_Plus:
                self._zoom_in()
                return
            elif event.key() == Qt.Key.Key_Minus:
                self._zoom_out()
                return
            elif event.key() == Qt.Key.Key_0:
                self._zoom_reset()
                return

        super().keyPressEvent(event)

    def _handle_auto_indent(self) -> None:
        cursor = self.textCursor()
        line = cursor.block().text()
        indent = ""
        for ch in line:
            if ch in (" ", "\t"):
                indent += ch
            else:
                break
        # Increase indent after colon
        stripped = line.rstrip()
        if stripped.endswith(":"):
            indent += "    "
        cursor.insertText("\n" + indent)
        self.setTextCursor(cursor)

    # ── Context Menu ─────────────────────────────────────────────────────

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        
        from friday_ai.brain.ai_actions.action_registry import action_registry
        
        has_selection = self.textCursor().hasSelection()
        actions = action_registry.get_applicable_actions(has_selection)
        
        if actions:
            menu.addSeparator()
            ai_menu = menu.addMenu("AI Actions ▶")
            for action in actions:
                qaction = ai_menu.addAction(action.display_name)
                # Need to use default arguments in lambda to capture loop variable
                qaction.triggered.connect(lambda checked=False, a=action: self._trigger_ai_action(a))
                
        menu.exec_(event.globalPos())
        
    def _trigger_ai_action(self, action):
        from friday_ai.brain.ai_actions.action_context import ActionContext, AIActionRequest
        from friday_ai.core.signals import signals
        import uuid
        
        cursor = self.textCursor()
        ctx = ActionContext(
            file_path=self._file_path,
            language=Path(self._file_path).suffix.lstrip("."),
            selected_text=cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else "",
            cursor_line=cursor.blockNumber() + 1,
            surrounding_code=""
        )
        
        request = AIActionRequest(
            request_id=str(uuid.uuid4()),
            action=action,
            context=ctx
        )
        
        signals.ai_action_requested.emit(request)


    # ── Editor Enhancements ──────────────────────────────────────────────

    def go_to_line(self) -> None:
        from PyQt5.QtWidgets import QInputDialog
        line, ok = QInputDialog.getInt(self, "Go to Line", "Line number:", min=1, max=self.blockCount())
        if ok:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, n=line-1)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    def duplicate_line(self) -> None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText()
            cursor.setPosition(cursor.selectionEnd())
            cursor.insertText(text)
        else:
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            text = cursor.selectedText()
            cursor.movePosition(QTextCursor.Down)
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.insertText(text + "\n")
            cursor.movePosition(QTextCursor.MoveOperation.Up)
            self.setTextCursor(cursor)

    def toggle_comment(self) -> None:
        cursor = self.textCursor()
        
        # If no selection, select the current line
        if not cursor.hasSelection():
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            
        start_block = self.document().findBlock(cursor.selectionStart())
        end_block = self.document().findBlock(cursor.selectionEnd())
        
        # If selection ends exactly at the start of a block, don't include that block
        if cursor.selectionEnd() == end_block.position() and end_block != start_block:
            end_block = end_block.previous()
            
        # Determine if we are commenting or uncommenting (if any line lacks #, we comment all)
        should_comment = False
        block = start_block
        while block.isValid() and block.position() <= end_block.position():
            text = block.text().lstrip()
            if text and not text.startswith("#"):
                should_comment = True
                break
            block = block.next()
            
        # Apply the toggle
        cursor.beginEditBlock()
        block = start_block
        while block.isValid() and block.position() <= end_block.position():
            cursor.setPosition(block.position())
            text = block.text()
            if not text.strip():
                pass # skip empty lines
            elif should_comment:
                # find first non-whitespace
                indent = len(text) - len(text.lstrip())
                cursor.setPosition(block.position() + indent)
                cursor.insertText("# ")
            else:
                # uncomment
                indent = len(text) - len(text.lstrip())
                if text[indent:].startswith("# "):
                    cursor.setPosition(block.position() + indent)
                    for _ in range(2): cursor.deleteChar()
                elif text[indent:].startswith("#"):
                    cursor.setPosition(block.position() + indent)
                    cursor.deleteChar()
            block = block.next()
            
        cursor.endEditBlock()

    # ── Zoom ─────────────────────────────────────────────────────────────

    def _zoom_in(self) -> None:
        self._zoom_level += 1
        self._apply_zoom()

    def _zoom_out(self) -> None:
        if self._base_font_size + self._zoom_level > 6:
            self._zoom_level -= 1
            self._apply_zoom()

    def _zoom_reset(self) -> None:
        self._zoom_level = 0
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        font = self.font()
        font.setPixelSize(self._base_font_size + self._zoom_level)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self._update_line_area_width()

    # ── Save support ─────────────────────────────────────────────────────

    def save(self) -> bool:
        """Save the file to disk. Returns True on success."""
        if not self._file_path:
            return False
        try:
            Path(self._file_path).write_text(
                self.toPlainText(), encoding="utf-8",
            )
            self.mark_saved()
            signals.file_saved.emit(self._file_path)
            signals.mission_update.emit("SAVE", f"Saved {Path(self._file_path).name}")
            return True
        except OSError:
            signals.mission_update.emit("ERROR", f"Failed to save {Path(self._file_path).name}")
            return False

    def save_as(self, new_path: str) -> bool:
        """Save to a new path."""
        old_path = self._file_path
        self._file_path = new_path
        self._setup_highlighter()
        if self.save():
            return True
        self._file_path = old_path
        return False
