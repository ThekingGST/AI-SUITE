from __future__ import annotations

import math
import random

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget


class Panel(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Panel")


class RadarWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.angle = 0
        self.blips = [(random.random(), random.random()) for _ in range(10)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def _tick(self) -> None:
        self.angle = (self.angle + 3) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2
        pen = QPen(QColor(34, 216, 255, 150), 1)
        painter.setPen(pen)
        for scale in (0.33, 0.66, 1.0):
            r = radius * scale
            painter.drawEllipse(center, int(r), int(r))
        angle_rad = math.radians(self.angle)
        end = QPointF(center.x() + math.cos(angle_rad) * radius, center.y() + math.sin(angle_rad) * radius)
        painter.setPen(QPen(QColor(34, 216, 255), 2))
        painter.drawLine(QPointF(center), end)
        painter.setBrush(QColor(255, 210, 82))
        painter.setPen(Qt.NoPen)
        for x, y in self.blips:
            painter.drawEllipse(QPointF(rect.left() + x * rect.width(), rect.top() + y * rect.height()), 3, 3)


class MetricPanel(Panel):
    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignCenter)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        layout.addWidget(self.label)
        layout.addWidget(self.bar)

    def set_value(self, value: float) -> None:
        self.bar.setValue(int(value))


class WaveformWidget(QWidget):
    """Animated microphone waveform used as a lightweight listening indicator."""

    def __init__(self) -> None:
        super().__init__()
        self.phase = 0.0
        self.active = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)
        self.setMinimumHeight(58)

    def set_active(self, active: bool) -> None:
        self.active = active

    def _tick(self) -> None:
        self.phase += 0.18 if self.active else 0.05
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        center = height / 2
        bar_count = 42
        gap = max(2, width / bar_count)
        color = QColor(34, 216, 255, 230 if self.active else 90)
        painter.setPen(QPen(color, 2))
        for index in range(bar_count):
            x = index * gap + gap / 2
            amp = 8 + (18 if self.active else 5) * abs(math.sin(self.phase + index * 0.35))
            painter.drawLine(QPointF(x, center - amp), QPointF(x, center + amp))


class StatusPill(QLabel):
    def __init__(self) -> None:
        super().__init__("SYSTEMS ONLINE")
        self._pulse = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(80)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(34)

    def set_status(self, text: str) -> None:
        self.setText(text.upper())

    def _tick(self) -> None:
        self._pulse = (self._pulse + 1) % 20
        alpha = 120 + abs(10 - self._pulse) * 9
        self.setStyleSheet(
            f"background: rgba(7, 45, 56, {alpha}); border: 1px solid #22d8ff; "
            "border-radius: 8px; color: #d7fbff; font-weight: 600;"
        )
