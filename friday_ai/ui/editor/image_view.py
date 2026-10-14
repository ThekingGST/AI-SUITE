"""Image preview widget for the editor area.

Displays images (PNG, JPG, SVG, etc.) with fit-to-window scaling and
basic metadata (dimensions, file size).
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from friday_ai.core.theme import THEME


_IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
})


def is_image_file(path: str) -> bool:
    """Check if the path has an image extension."""
    return Path(path).suffix.lower() in _IMAGE_EXTENSIONS


class ImageView(QWidget):
    """Display an image with metadata."""

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Info bar
        p = Path(self._path)
        size_kb = p.stat().st_size / 1024
        info_text = f"{p.name}  |  {size_kb:.1f} KB"

        info = QLabel(info_text)
        info.setAlignment(Qt.AlignCenter)
        info.setFixedHeight(32)
        info.setStyleSheet(
            f"background: {THEME.bg_overlay}; "
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_xs}px; "
            f"border-bottom: {THEME.border_width}px solid {THEME.border_muted};"
        )
        layout.addWidget(info)

        # Image
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {THEME.bg_inset}; border: none; }}"
        )

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("background: transparent;")

        pixmap = QPixmap(self._path)
        if not pixmap.isNull():
            # Scale to fit reasonably
            scaled = pixmap.scaled(
                800, 600,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_label.setPixmap(scaled)
            info.setText(
                f"{p.name}  |  {pixmap.width()}x{pixmap.height()}  |  {size_kb:.1f} KB"
            )
        else:
            img_label.setText("Unable to load image")
            img_label.setStyleSheet(
                f"color: {THEME.text_muted}; "
                f"font-size: {THEME.font_size_base}px;"
            )

        scroll.setWidget(img_label)
        layout.addWidget(scroll, stretch=1)
