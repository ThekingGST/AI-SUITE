from __future__ import annotations

import cv2
import numpy as np
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap


def cv_to_pixmap(frame: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, channels = rgb.shape
    bytes_per_line = channels * w
    image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())


def offline_hologram_pixmap(width: int, height: int, tick: int) -> QPixmap:
    pixmap = QPixmap(max(1, width), max(1, height))
    pixmap.fill(QColor(3, 13, 18))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    grid_color = QColor(34, 216, 255, 48)
    painter.setPen(QPen(grid_color, 1))
    spacing = 36
    offset = tick % spacing
    for x in range(-spacing + offset, width, spacing):
        painter.drawLine(x, 0, x, height)
    for y in range(-spacing + offset, height, spacing):
        painter.drawLine(0, y, width, y)

    center = QPointF(width / 2, height / 2)
    radius = min(width, height) * 0.24
    painter.setPen(QPen(QColor(34, 216, 255, 140), 2))
    for scale in (1.0, 0.68, 0.36):
        painter.drawEllipse(center, radius * scale, radius * scale)
    angle = (tick * 3) % 360
    import math

    end = QPointF(
        center.x() + math.cos(math.radians(angle)) * radius,
        center.y() + math.sin(math.radians(angle)) * radius,
    )
    painter.setPen(QPen(QColor(34, 216, 255, 230), 3))
    painter.drawLine(center, end)

    painter.setPen(QPen(QColor(34, 216, 255, 70), 1))
    for y in range((tick * 2) % 8, height, 8):
        painter.drawLine(0, y, width, y)

    painter.setPen(QColor(215, 251, 255))
    font = QFont("Segoe UI", max(18, min(width, height) // 18), QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "CAMERA DISABLED")
    painter.setFont(QFont("Segoe UI", max(10, min(width, height) // 38)))
    painter.setPen(QColor(143, 225, 238))
    painter.drawText(pixmap.rect().adjusted(0, 72, 0, 0), Qt.AlignCenter, "Awaiting camera activation...")
    painter.end()
    return pixmap
