"""AI Suite Boot Screen — Frameless centered boot window.

This is the top-level visual container for the boot experience.
It renders a pure black frameless window centered on screen with
rounded corners and a soft cyan drop shadow.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QDesktopWidget,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
)
from PyQt5.QtGui import (
    QPainter, QPainterPath, QColor, QBrush, QRadialGradient
)
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
)

from ai_suite.ui.boot.boot_theme import (
    BG_COLOR, CYAN_GLOW, SHADOW_COLOR, SHADOW_BLUR_RADIUS,
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_CORNER_RADIUS, WINDOW_MARGIN,
    PHASE1_DELAY_MS, REACTOR_SIZE, MESSAGES_CONTAINER_MIN_WIDTH,
    TRANSITION_GLOW_MS, TRANSITION_FADE_MS
)
from ai_suite.ui.boot.arc_reactor import ArcReactor
from ai_suite.ui.boot.boot_messages import BootMessages


class BootOverlay(QWidget):
    """Premium boot sequence overlay that reveals the dashboard."""

    skip_requested = pyqtSignal()
    transition_complete = pyqtSignal()
    transition_halfway = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Overlay should cover the parent entirely, no top-level flags needed
        self.setObjectName("BootOverlay")

        # ── Internal state ──────────────────────────────────────
        self._phase = 0  # 0: init, 1: phase 1, 2: transitioning
        self._glow_radius = 0.0

        # Removed translucent background to test for crash

        self._build_layout()

    def _build_layout(self):
        """Build the vertical layout with the Arc Reactor centered."""
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN, WINDOW_MARGIN)
        self._root_layout.setAlignment(Qt.AlignCenter)

        self._root_layout.addStretch(1)

        # ── Arc Reactor ─────────────────────────────────────────
        self.reactor = ArcReactor(self)
        self.reactor.setMinimumSize(REACTOR_SIZE, REACTOR_SIZE)
        self._root_layout.addWidget(self.reactor, 0, Qt.AlignCenter)



        # ── Messages ────────────────────────────────────────────
        self.messages = BootMessages(self)
        self.messages.setMinimumWidth(MESSAGES_CONTAINER_MIN_WIDTH)
        self._root_layout.addWidget(self.messages, 0, Qt.AlignCenter)

        self._root_layout.addStretch(1)

    # ── Painting ────────────────────────────────────────────────

    def paintEvent(self, event):
        """Draw rounded-corner black background."""
        painter = QPainter()
        if not painter.begin(self):
            return
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        from PyQt5.QtCore import QRectF
        path.addRoundedRect(QRectF(self.rect()), WINDOW_CORNER_RADIUS, WINDOW_CORNER_RADIUS)
        painter.fillPath(path, BG_COLOR)
        
        # If in transition, draw the expanding cyan glow
        if self._glow_radius > 0:
            from PyQt5.QtCore import QPointF
            center = self.rect().center()
            grad = QRadialGradient(QPointF(center.x(), center.y()), self._glow_radius)
            # Center is solid cyan
            grad.setColorAt(0.0, QColor(CYAN_GLOW.red(), CYAN_GLOW.green(), CYAN_GLOW.blue(), 255))
            # Edges fade to transparent
            grad.setColorAt(1.0, QColor(CYAN_GLOW.red(), CYAN_GLOW.green(), CYAN_GLOW.blue(), 0))
            
            painter.setCompositionMode(QPainter.CompositionMode_Screen)
            painter.fillPath(path, QBrush(grad))
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        painter.end()

    # ── Properties ──────────────────────────────────────────────
    
    @pyqtProperty(float)
    def glowRadius(self):
        return self._glow_radius

    @glowRadius.setter
    def glowRadius(self, value):
        self._glow_radius = value
        self.update()

    # ── Keyboard ────────────────────────────────────────────────

    def keyPressEvent(self, event):
        """ESC immediately skips the boot animation."""
        if event.key() == Qt.Key_Escape:
            self.skip_requested.emit()
        else:
            super().keyPressEvent(event)

    def stop_animations(self):
        """Immediately stops all visual animations for an ESC skip."""
        self._phase = 2
        for anim in self.messages._animations:
            if anim.state() == QPropertyAnimation.Running:
                anim.stop()
        if hasattr(self, '_glow_anim') and self._glow_anim.state() == QPropertyAnimation.Running:
            self._glow_anim.stop()
        if hasattr(self, '_fade_anim') and self._fade_anim.state() == QPropertyAnimation.Running:
            self._fade_anim.stop()

    # ── Phase control (called by BootController) ────────────────

    def begin_phase1(self):
        """Start Phase 1: pure black for PHASE1_DELAY_MS, then advance."""
        self._phase = 0
        self.show()
        QTimer.singleShot(PHASE1_DELAY_MS, self._advance_to_phase2)

    def _advance_to_phase2(self):
        """Phase 2: reactor core appears."""
        self._phase = 1
        self.reactor.set_reactor_level(1)  # Core glow

    def add_message(self, text: str):
        """Pass-through to add a message to the UI."""
        self.messages.add_message(text)

    def set_greeting(self, text: str):
        """Pass-through to add the final greeting to the UI."""
        self.messages.set_greeting(text)

    # ── Public API for transition (Step 6) ──────────────────────

    def start_transition(self):
        """Phase 6: final transition."""
        self._phase = 2
        
        # 0. Dissolve rings and core, leaving just the glow (Level 9)
        self.reactor.set_reactor_level(9)
        
        # 1. Expand bloom
        self._glow_anim = QPropertyAnimation(self, b"glowRadius")
        self._glow_anim.setDuration(TRANSITION_GLOW_MS)
        self._glow_anim.setStartValue(0.0)
        self._glow_anim.setEndValue(1200.0)  # Larger than window diagonal
        self._glow_anim.setEasingCurve(QEasingCurve.InCubic)
        
        # 2. Wait 400ms into the bloom, then emit halfway
        QTimer.singleShot(400, self.transition_halfway.emit)
        
        # 3. After glow expands fully, start fade out
        self._glow_anim.finished.connect(self._start_fade_out)
        
        # Start animations after a tiny delay so dissolve starts slightly earlier
        QTimer.singleShot(200, self._glow_anim.start)
        
    def _start_fade_out(self):
        self._overlay_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._overlay_effect)
        
        self._fade_anim = QPropertyAnimation(self._overlay_effect, b"opacity")
        self._fade_anim.setDuration(TRANSITION_FADE_MS)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.close_boot)
        self._fade_anim.start()

    def close_boot(self):
        """Clean shutdown of the boot overlay."""
        self.transition_complete.emit()
        self.deleteLater()
