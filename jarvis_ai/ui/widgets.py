from __future__ import annotations

import math
import random

from PyQt5.QtCore import QPointF, Qt, QTimer, QSize
from PyQt5.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QSizePolicy
from PyQt5.QtGui import QIcon, QColor, QPainter, QPen
import os
from jarvis_ai.config import PROJECT_ROOT


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
        if not self.isVisible():
            return
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
        if not self.isVisible():
            return
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
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(34)

    def showEvent(self, event) -> None:
        self.timer.start(80)

    def hideEvent(self, event) -> None:
        self.timer.stop()

    def set_status(self, text: str) -> None:
        self.setText(text.upper())

    def _tick(self) -> None:
        if not self.isVisible():
            return
        self._pulse = (self._pulse + 1) % 20
        alpha = 120 + abs(10 - self._pulse) * 9
        self.setStyleSheet(
            f"background: rgba(7, 45, 56, {alpha}); border: 1px solid #22d8ff; "
            "border-radius: 8px; color: #d7fbff; font-weight: 600;"
        )

class ControlChip(QPushButton):
    """Modern modular control button containing an SVG icon and a short text label."""
    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        icon_path = os.path.join(PROJECT_ROOT, "assets", "icons", f"{icon_name}.svg")
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(18, 18))
        self._update_stylesheet(active=True, error=False)

    def set_state(self, active: bool, error: bool = False):
        self._update_stylesheet(active, error)

    def _update_stylesheet(self, active: bool, error: bool):
        if error:
            bg, border, hover, text = "rgba(255, 64, 87, 0.15)", "#ff4057", "rgba(255, 64, 87, 0.25)", "#ffe8ec"
        elif active:
            bg, border, hover, text = "rgba(34, 216, 255, 0.08)", "rgba(34, 216, 255, 0.3)", "rgba(34, 216, 255, 0.15)", "#e8fdff"
        else:
            bg, border, hover, text = "rgba(255, 255, 255, 0.02)", "rgba(255, 255, 255, 0.1)", "rgba(255, 255, 255, 0.08)", "#a0b4c4"
            
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
                color: {text};
                padding: 4px 8px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {hover};
            }}
        """)

class IconLabel(QWidget):
    """A minimal horizontal widget wrapping a 16x16 SVG icon and a text label."""
    def __init__(self, icon_name: str, initial_text: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)
        
        self.icon_label = QLabel()
        icon_path = os.path.join(PROJECT_ROOT, "assets", "icons", f"{icon_name}.svg")
        self.icon_label.setPixmap(QIcon(icon_path).pixmap(16, 16))
        self.icon_label.setFixedSize(16, 16)
        
        self.text_label = QLabel(initial_text)
        self.text_label.setStyleSheet("color: #8b9fb0; font-size: 11px;")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        
    def setText(self, text: str):
        self.text_label.setText(text)
        
    def setIcon(self, icon_name: str):
        icon_path = os.path.join(PROJECT_ROOT, "assets", "icons", f"{icon_name}.svg")
        self.icon_label.setPixmap(QIcon(icon_path).pixmap(16, 16))
