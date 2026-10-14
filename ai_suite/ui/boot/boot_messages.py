"""AI Suite Boot Screen — Boot Messages widget.

Displays the main title, subtitle, and an animated list of initialization milestones.
Each milestone fades in smoothly when added.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve

from ai_suite.ui.boot.boot_theme import (
    TEXT_PRIMARY, TEXT_DIM, TEXT_SUCCESS,
    CYAN_PRIMARY,
    make_font, STAGE_ANIM_DURATION_MS,
    TITLE_FONT_SIZE, TITLE_LETTER_SPACING,
    SUBTITLE_FONT_SIZE, SUBTITLE_LETTER_SPACING,
    MESSAGE_FONT_SIZE, MESSAGE_ITEM_MIN_WIDTH,
    GREETING_FONT_SIZE, GREETING_ANIM_DURATION_MS,
    MESSAGES_SPACING_MAIN, MESSAGES_SPACING_ITEMS,
    TITLE_BOTTOM_MARGIN, GREETING_TOP_MARGIN
)

class BootMessages(QWidget):
    """Container for the boot titles and animated message log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(MESSAGES_SPACING_MAIN)
        self._layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # ── Titles ──────────────────────────────────────────────
        
        self.title_label = QLabel("A I · S U I T E")
        self.title_label.setFont(make_font(TITLE_FONT_SIZE, letter_spacing=TITLE_LETTER_SPACING))
        self.title_label.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.subtitle_label = QLabel("J A R V I S")
        self.subtitle_label.setFont(make_font(SUBTITLE_FONT_SIZE, letter_spacing=SUBTITLE_LETTER_SPACING))
        self.subtitle_label.setStyleSheet(f"color: {CYAN_PRIMARY.name()};")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        
        self._layout.addWidget(self.title_label)
        self._layout.addWidget(self.subtitle_label)
        
        self._layout.addSpacing(TITLE_BOTTOM_MARGIN)

        # ── Message List Container ──────────────────────────────
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(MESSAGES_SPACING_ITEMS)
        self.messages_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        self._layout.addWidget(self.messages_container)
        
        # Keep track of animations to prevent garbage collection
        self._animations = []

    def add_message(self, text: str):
        """Add a new milestone line with a fade-in animation."""
        label = QLabel(f"✓ {text}")
        label.setFont(make_font(MESSAGE_FONT_SIZE))
        
        # Styling: checkmark is success color, text is dim
        color_hex = TEXT_DIM.name()
        success_hex = TEXT_SUCCESS.name()
        label.setText(f'<font color="{success_hex}">✓</font> <font color="{color_hex}">{text}</font>')
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Ensure consistent width for left alignment of the block
        label.setMinimumWidth(MESSAGE_ITEM_MIN_WIDTH)

        effect = QGraphicsOpacityEffect(label)
        effect.setOpacity(0.0)
        label.setGraphicsEffect(effect)

        self.messages_layout.addWidget(label)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(STAGE_ANIM_DURATION_MS)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        
        self._animations.append(anim)
        
        # Clean up finished animations
        anim.finished.connect(lambda a=anim: self._remove_animation(a))

    def _remove_animation(self, anim):
        if anim in self._animations:
            self._animations.remove(anim)

    def set_greeting(self, text: str):
        """Adds the final welcome message."""
        self._layout.addSpacing(GREETING_TOP_MARGIN)
        
        label = QLabel(text)
        label.setFont(make_font(GREETING_FONT_SIZE))
        label.setStyleSheet(f"color: {TEXT_PRIMARY.name()};")
        label.setAlignment(Qt.AlignCenter)
        
        effect = QGraphicsOpacityEffect(label)
        effect.setOpacity(0.0)
        label.setGraphicsEffect(effect)
        
        self._layout.addWidget(label)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(GREETING_ANIM_DURATION_MS)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self._animations.append(anim)
        anim.finished.connect(lambda a=anim: self._remove_animation(a))
