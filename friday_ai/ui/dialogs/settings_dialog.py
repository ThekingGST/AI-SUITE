"""Settings dialog — configuration for the IDE."""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout, QWidget, QCheckBox
)
from friday_ai.core.theme import THEME
from friday_ai.services.persistence import WorkspacePersistence


class SettingsDialog(QDialog):
    """IDE settings configuration."""

    def __init__(self, persistence: WorkspacePersistence, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._persistence = persistence
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self.setStyleSheet(
            f"QDialog {{ background: {THEME.bg_base}; }}"
            f"QLabel {{ color: {THEME.text_primary}; }}"
        )
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_xl, THEME.space_xl, THEME.space_xl, THEME.space_xl)
        layout.setSpacing(THEME.space_xl)

        # Editor settings
        editor_group = self._create_group("Editor")
        
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 32)
        self._font_size.setValue(THEME.font_size_base)
        editor_group.addWidget(self._create_row("Font Size:", self._font_size))

        self._tab_width = QSpinBox()
        self._tab_width.setRange(2, 8)
        self._tab_width.setValue(4)
        editor_group.addWidget(self._create_row("Tab Width:", self._tab_width))

        self._word_wrap = QCheckBox("Enable Word Wrap")
        editor_group.addWidget(self._word_wrap)

        layout.addWidget(editor_group)

        # Terminal settings
        term_group = self._create_group("Terminal")
        self._shell = QComboBox()
        self._shell.addItems(["PowerShell", "CMD", "Git Bash"])
        term_group.addWidget(self._create_row("Default Shell:", self._shell))
        layout.addWidget(term_group)

        layout.addStretch()

        # Buttons
        btns = QWidget()
        btn_layout = QHBoxLayout(btns)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        save = QPushButton("Save")
        save.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(save)
        
        layout.addWidget(btns)

    def _create_group(self, title: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(THEME.space_md)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {THEME.text_secondary}; font-weight: bold; font-size: {THEME.font_size_sm}px;")
        l.addWidget(lbl)
        return w

    def _create_row(self, label: str, widget: QWidget) -> QWidget:
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(QLabel(label))
        l.addStretch()
        l.addWidget(widget)
        return w
