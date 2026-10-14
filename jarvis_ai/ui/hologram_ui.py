from __future__ import annotations

import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap


def cv_to_pixmap(frame: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, channels = rgb.shape
    bytes_per_line = channels * w
    image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(image.copy())
