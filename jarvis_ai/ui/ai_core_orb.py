from __future__ import annotations

import math
import random
from enum import Enum

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen, QRadialGradient
from PyQt5.QtWidgets import QWidget


class OrbState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"
    CAMERA_DISABLED = "CAMERA_DISABLED"


class AICoreOrb(QWidget):
    """Animated holographic core that represents JARVIS independent of camera state."""

    def __init__(self) -> None:
        super().__init__()
        self.state = OrbState.IDLE
        self.phase = 0.0
        self.particles = [(random.random(), random.random(), random.random()) for _ in range(28)]
        self.setMinimumSize(160, 160)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def set_state(self, state: OrbState | str) -> None:
        self.state = state if isinstance(state, OrbState) else OrbState(str(state))
        self.update()

    def _tick(self) -> None:
        speed = {
            OrbState.IDLE: 0.045,
            OrbState.LISTENING: 0.09,
            OrbState.THINKING: 0.13,
            OrbState.SPEAKING: 0.16,
            OrbState.ERROR: 0.08,
            OrbState.OFFLINE: 0.025,
            OrbState.CAMERA_DISABLED: 0.06,
        }[self.state]
        self.phase = (self.phase + speed) % (math.pi * 2)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        center = QPointF(rect.center())
        radius = min(rect.width(), rect.height()) * 0.29
        color = self._state_color()

        glow = QRadialGradient(center, radius * 2.6)
        glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 210))
        glow.setColorAt(0.45, QColor(color.red(), color.green(), color.blue(), 60))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, radius * 2.2, radius * 2.2)

        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 180), 2))
        for index, scale in enumerate((1.08, 1.34, 1.72)):
            wobble = math.sin(self.phase + index * 1.7) * 7
            orbit = rect.adjusted(
                int(rect.width() * (0.5 - scale * 0.18)),
                int(rect.height() * (0.5 - scale * 0.12)),
                -int(rect.width() * (0.5 - scale * 0.18)),
                -int(rect.height() * (0.5 - scale * 0.12)),
            )
            start = int((self.phase * (36 if index % 2 == 0 else -42) + index * 80) * 16)
            painter.drawArc(orbit, start, int((170 + wobble * 4) * 16))

        ripple_alpha = 80 + int(55 * abs(math.sin(self.phase * 1.4)))
        painter.setPen(QPen(QColor(215, 251, 255, ripple_alpha), 1))
        for scale in (0.42, 0.62, 0.82):
            painter.drawEllipse(center, radius * scale, radius * scale)

        painter.setBrush(QColor(180, 248, 255, 210))
        painter.setPen(QPen(QColor(34, 216, 255, 230), 2))
        painter.drawEllipse(center, radius, radius)

        inner = QRadialGradient(center, radius)
        inner.setColorAt(0.0, QColor(255, 255, 255, 235))
        inner.setColorAt(0.35, QColor(color.red(), color.green(), color.blue(), 210))
        inner.setColorAt(1.0, QColor(5, 34, 42, 40))
        painter.setBrush(inner)
        painter.setPen(QPen(QColor(215, 251, 255, 180), 1))
        painter.drawEllipse(center, radius * 0.58, radius * 0.58)

        painter.setPen(Qt.NoPen)
        for x, y, drift in self.particles:
            stream = self.phase * (0.024 if self.state in (OrbState.THINKING, OrbState.SPEAKING) else 0.012)
            px = rect.left() + ((x + stream * (drift + 0.3)) % 1.0) * rect.width()
            py = rect.top() + ((y + math.sin(self.phase * 1.8 + drift * 4) * 0.028) % 1.0) * rect.height()
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 70 + int(110 * drift)))
            painter.drawEllipse(QPointF(px, py), 1.8 + drift * 2.4, 1.8 + drift * 2.4)

        painter.setPen(QColor(215, 251, 255))
        painter.drawText(rect, Qt.AlignHCenter | Qt.AlignBottom, self.state.value.replace("_", " "))

    def _state_color(self) -> QColor:
        return {
            OrbState.IDLE: QColor(34, 216, 255),
            OrbState.LISTENING: QColor(48, 255, 210),
            OrbState.THINKING: QColor(255, 210, 82),
            OrbState.SPEAKING: QColor(92, 235, 255),
            OrbState.ERROR: QColor(255, 166, 54),
            OrbState.OFFLINE: QColor(92, 120, 130),
            OrbState.CAMERA_DISABLED: QColor(45, 170, 255),
        }[self.state]
