"""Settings page — configuration for the IDE shown as an editor tab."""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout, QWidget, QCheckBox, QScrollArea
)
from friday_ai.core.theme import THEME


class SettingsPage(QWidget):
    """IDE settings configuration page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {THEME.bg_base}; }}")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(THEME.space_3xl, THEME.space_3xl, THEME.space_3xl, THEME.space_3xl)
        content_layout.setSpacing(THEME.space_xl)
        content_layout.setAlignment(Qt.AlignTop)

        title = QLabel("Settings")
        title.setStyleSheet(f"color: {THEME.text_primary}; font-size: {THEME.font_size_title}px; font-weight: bold;")
        content_layout.addWidget(title)

        # Editor settings
        editor_group = self._create_group("Editor")
        
        self._font_size = QSpinBox()
        self._font_size.setRange(8, 32)
        self._font_size.setValue(THEME.font_size_base)
        editor_group.layout().addWidget(self._create_row("Font Size:", self._font_size))

        self._tab_width = QSpinBox()
        self._tab_width.setRange(2, 8)
        self._tab_width.setValue(4)
        editor_group.layout().addWidget(self._create_row("Tab Width:", self._tab_width))

        self._word_wrap = QCheckBox("Enable Word Wrap")
        editor_group.layout().addWidget(self._word_wrap)

        content_layout.addWidget(editor_group)

        # Terminal settings
        term_group = self._create_group("Terminal")
        self._shell = QComboBox()
        self._shell.addItems(["PowerShell", "CMD", "Git Bash"])
        term_group.layout().addWidget(self._create_row("Default Shell:", self._shell))
        content_layout.addWidget(term_group)

        # Python settings
        py_group = self._create_group("Python")
        self._interpreter = QComboBox()
        self._interpreter.addItem("Default Environment")
        py_group.layout().addWidget(self._create_row("Interpreter:", self._interpreter))
        content_layout.addWidget(py_group)
        
        # Theme
        theme_group = self._create_group("Theme")
        self._theme = QComboBox()
        self._theme.addItems(["Dark (Default)"])
        theme_group.layout().addWidget(self._create_row("Color Theme:", self._theme))
        content_layout.addWidget(theme_group)

        content_layout.addStretch()

        # Buttons
        btns = QWidget()
        btn_layout = QHBoxLayout(btns)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        save = QPushButton("Save Settings")
        save.setFixedWidth(150)
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.setStyleSheet(
            f"QPushButton {{ background: {THEME.accent_muted}; color: {THEME.text_on_accent};"
            f" border: none; padding: {THEME.space_md}px; border-radius: {THEME.radius_sm}px; }}"
            f"QPushButton:hover {{ background: {THEME.accent}; }}"
        )
        btn_layout.addWidget(save)
        btn_layout.addStretch()
        
        content_layout.addWidget(btns)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_group(self, title: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, THEME.space_lg)
        l.setSpacing(THEME.space_md)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {THEME.text_secondary}; font-weight: bold; font-size: {THEME.font_size_lg}px;")
        l.addWidget(lbl)
        return w

    def _create_row(self, label: str, widget: QWidget) -> QWidget:
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFixedWidth(150)
        lbl.setStyleSheet(f"color: {THEME.text_primary};")
        widget.setFixedWidth(200)
        l.addWidget(lbl)
        l.addWidget(widget)
        l.addStretch()
        return w
