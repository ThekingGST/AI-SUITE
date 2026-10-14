"""Search and Replace bar for the code editor.

Provides a togglable panel at the top of the editor area with:
    * Find (Ctrl+F) — highlight all matches, navigate with Enter/Shift+Enter
    * Replace (Ctrl+H) — replace current or all matches
    * Match count indicator
"""

from __future__ import annotations

import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.icons import Icons
from friday_ai.core.theme import THEME


class SearchBar(QWidget):
    """Inline search and replace bar."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editor = None  # Will be set via set_editor()
        self._matches: list[tuple[int, int]] = []
        self._current_match = -1
        self._build_ui()
        self.hide()

    def set_editor(self, editor) -> None:
        """Bind the search bar to a CodeEditor instance."""
        self._editor = editor

    # ── Construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            THEME.space_xl, THEME.space_md, THEME.space_xl, THEME.space_md,
        )
        layout.setSpacing(THEME.space_sm)

        self.setStyleSheet(
            f"background: {THEME.bg_overlay}; "
            f"border-bottom: {THEME.border_width}px solid {THEME.border_default};"
        )

        # Find row
        find_row = QHBoxLayout()
        find_row.setSpacing(THEME.space_md)

        find_label = QLabel("Find:")
        find_label.setStyleSheet(
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_sm}px; "
            "background: transparent;"
        )
        find_row.addWidget(find_label)

        self._find_input = self._make_input("Search...")
        self._find_input.textChanged.connect(self._on_find_changed)
        self._find_input.returnPressed.connect(self.find_next)
        find_row.addWidget(self._find_input, stretch=1)

        self._match_label = QLabel("")
        self._match_label.setStyleSheet(
            f"color: {THEME.text_muted}; "
            f"font-size: {THEME.font_size_xs}px; "
            "background: transparent; "
            "min-width: 60px;"
        )
        find_row.addWidget(self._match_label)

        prev_btn = self._make_button("Prev", self.find_prev)
        find_row.addWidget(prev_btn)
        next_btn = self._make_button("Next", self.find_next)
        find_row.addWidget(next_btn)

        close_btn = QPushButton()
        close_btn.setIcon(Icons.get("close", color=THEME.text_muted, size=14))
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"border-radius: {THEME.radius_sm}px; }}"
            f"QPushButton:hover {{ background: {THEME.bg_active}; }}"
        )
        close_btn.clicked.connect(self.close_bar)
        find_row.addWidget(close_btn)

        layout.addLayout(find_row)

        # Replace row
        self._replace_row = QWidget()
        replace_layout = QHBoxLayout(self._replace_row)
        replace_layout.setContentsMargins(0, 0, 0, 0)
        replace_layout.setSpacing(THEME.space_md)

        replace_label = QLabel("Replace:")
        replace_label.setStyleSheet(
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_sm}px; "
            "background: transparent;"
        )
        replace_layout.addWidget(replace_label)

        self._replace_input = self._make_input("Replace...")
        replace_layout.addWidget(self._replace_input, stretch=1)

        replace_btn = self._make_button("Replace", self._replace_one)
        replace_layout.addWidget(replace_btn)
        replace_all_btn = self._make_button("Replace All", self._replace_all)
        replace_layout.addWidget(replace_all_btn)

        # Spacer to match close button width
        spacer = QWidget()
        spacer.setFixedWidth(22)
        spacer.setStyleSheet("background: transparent;")
        replace_layout.addWidget(spacer)

        self._replace_row.hide()
        layout.addWidget(self._replace_row)

    def _make_input(self, placeholder: str) -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(28)
        inp.setStyleSheet(
            f"QLineEdit {{ "
            f"  background: {THEME.bg_inset}; "
            f"  color: {THEME.text_primary}; "
            f"  border: {THEME.border_width}px solid {THEME.border_default}; "
            f"  border-radius: {THEME.radius_sm}px; "
            f"  padding: 0 {THEME.space_md}px; "
            f"  font-size: {THEME.font_size_sm}px; "
            f"  font-family: {THEME.font_mono}; "
            f"}} "
            f"QLineEdit:focus {{ "
            f"  border-color: {THEME.accent}; "
            f"}}"
        )
        return inp

    def _make_button(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ "
            f"  background: {THEME.bg_active}; "
            f"  color: {THEME.text_secondary}; "
            f"  border: none; "
            f"  border-radius: {THEME.radius_sm}px; "
            f"  padding: 0 {THEME.space_lg}px; "
            f"  font-size: {THEME.font_size_xs}px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"  background: {THEME.accent_muted}; "
            f"  color: {THEME.text_primary}; "
            f"}}"
        )
        btn.clicked.connect(callback)
        return btn

    # ── Public API ───────────────────────────────────────────────────────

    def open_find(self) -> None:
        """Show the search bar in find mode."""
        self._replace_row.hide()
        self.show()
        self._find_input.setFocus()
        self._find_input.selectAll()

    def open_replace(self) -> None:
        """Show the search bar in find+replace mode."""
        self._replace_row.show()
        self.show()
        self._find_input.setFocus()
        self._find_input.selectAll()

    def close_bar(self) -> None:
        """Hide the search bar and clear highlights."""
        self.hide()
        self._clear_highlights()
        if self._editor:
            self._editor.setFocus()

    # ── Find logic ───────────────────────────────────────────────────────

    def _on_find_changed(self, text: str) -> None:
        self._find_matches(text)
        if self._matches:
            self._current_match = 0
            self._go_to_match(0)
        else:
            self._current_match = -1
        self._update_label()

    def _find_matches(self, text: str) -> None:
        self._matches = []
        if not text or not self._editor:
            self._clear_highlights()
            return
        content = self._editor.toPlainText()
        try:
            pattern = re.escape(text)
            for m in re.finditer(pattern, content, re.IGNORECASE):
                self._matches.append((m.start(), m.end()))
        except re.error:
            pass
        self._highlight_all()

    def _highlight_all(self) -> None:
        if not self._editor:
            return
        selections = []
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#5a4a00"))
        fmt.setForeground(QColor(THEME.text_primary))

        for start, end in self._matches:
            sel = QTextEdit.ExtraSelection()
            cursor = QTextCursor(self._editor.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        # Keep the current-line highlight from the editor
        editor_sels = self._editor.extraSelections()
        # Filter out previous search highlights (those with our specific background)
        non_search = [
            s for s in editor_sels
            if s.format.background().color() != QColor("#5a4a00")
        ]
        self._editor.setExtraSelections(non_search + selections)

    def _clear_highlights(self) -> None:
        if not self._editor:
            return
        sels = self._editor.extraSelections()
        non_search = [
            s for s in sels
            if s.format.background().color() != QColor("#5a4a00")
        ]
        self._editor.setExtraSelections(non_search)

    def _go_to_match(self, index: int) -> None:
        if not self._editor or not self._matches:
            return
        start, end = self._matches[index]
        cursor = self._editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(cursor)
        self._editor.centerCursor()

    def _update_label(self) -> None:
        total = len(self._matches)
        if total == 0:
            query = self._find_input.text()
            self._match_label.setText("No results" if query else "")
        else:
            self._match_label.setText(f"{self._current_match + 1} of {total}")

    def find_next(self) -> None:
        if not self._matches:
            return
        self._current_match = (self._current_match + 1) % len(self._matches)
        self._go_to_match(self._current_match)
        self._update_label()

    def find_prev(self) -> None:
        if not self._matches:
            return
        self._current_match = (self._current_match - 1) % len(self._matches)
        self._go_to_match(self._current_match)
        self._update_label()

    # ── Replace logic ────────────────────────────────────────────────────

    def _replace_one(self) -> None:
        if not self._editor or not self._matches or self._current_match < 0:
            return
        start, end = self._matches[self._current_match]
        replacement = self._replace_input.text()
        cursor = self._editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
        self._editor.setTextCursor(cursor)
        self._on_find_changed(self._find_input.text())

    def _replace_all(self) -> None:
        if not self._editor or not self._matches:
            return
        query = self._find_input.text()
        replacement = self._replace_input.text()
        content = self._editor.toPlainText()
        new_content = content.replace(query, replacement)
        if new_content != content:
            count = content.count(query)
            cursor = self._editor.textCursor()
            cursor.beginEditBlock()
            self._editor.selectAll()
            self._editor.textCursor().insertText(new_content)
            cursor.endEditBlock()
            signals.mission_update.emit("EDIT", f"Replaced {count} occurrences")
        self._on_find_changed(self._find_input.text())

    # ── Keyboard ─────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        if event.key() == Qt.Key.Key_Return:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.find_prev()
            else:
                self.find_next()
            return
        super().keyPressEvent(event)
