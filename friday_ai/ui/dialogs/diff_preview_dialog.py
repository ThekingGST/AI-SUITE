"""Diff Preview Dialog: Displays proposed AI edits for user review."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QClipboard
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from friday_ai.brain.editing.change_set import ChangeSet
from friday_ai.brain.editing.preview_generator import PreviewGenerator
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from friday_ai.ui.editor.code_editor import CodeEditor


class DiffPreviewDialog(QDialog):
    """A professional dialog for reviewing and applying AI edits."""

    def __init__(self, change_set: ChangeSet, parent=None) -> None:
        super().__init__(parent)
        self.change_set = change_set
        self.setWindowTitle("Review AI Changes")
        self.resize(1000, 700)
        
        self.setStyleSheet(f"""
            QDialog {{ background: {THEME.bg_base}; color: {THEME.text_primary}; }}
            QLabel {{ color: {THEME.text_primary}; }}
            QPushButton {{ 
                background: {THEME.bg_surface}; 
                color: {THEME.text_primary}; 
                border: 1px solid {THEME.bg_inset}; 
                padding: 6px 16px; 
                border-radius: 4px;
            }}
            QPushButton:hover {{ background: {THEME.bg_inset}; }}
            QPushButton#ApplyBtn {{
                background: {THEME.accent}; 
                color: white; 
                border: none;
            }}
            QPushButton#ApplyBtn:hover {{ background: {THEME.accent_muted}; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QLabel(f"<b>Proposed changes for:</b> {self.change_set.file_path}<br/>"
                        f"<small>{self.change_set.summary}</small>")
        layout.addWidget(header)
        
        # Unified Diff Viewer
        self.viewer = CodeEditor(parent=self)
        self.viewer.setReadOnly(True)
        # We can pretend it's a diff file so CodeEditor might use diff syntax highlighting if available
        # But we'll just set the text directly.
        diff_text = PreviewGenerator.generate_unified_diff(self.change_set)
        if not diff_text.strip():
            diff_text = "No structural changes detected."
            
        self.viewer.setPlainText(diff_text)
        layout.addWidget(self.viewer)
        
        # Footer
        footer = QHBoxLayout()
        
        reject_btn = QPushButton("Reject")
        reject_btn.clicked.connect(self.reject)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_diff)
        
        apply_btn = QPushButton("Apply Changes")
        apply_btn.setObjectName("ApplyBtn")
        apply_btn.clicked.connect(self._apply)
        
        footer.addWidget(reject_btn)
        footer.addStretch()
        footer.addWidget(copy_btn)
        footer.addWidget(apply_btn)
        
        layout.addLayout(footer)

    def _copy_diff(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.viewer.toPlainText())

    def _apply(self) -> None:
        signals.diff_apply_requested.emit(self.change_set)
        self.accept()
