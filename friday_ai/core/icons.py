"""SVG icon loader with runtime recolouring.

Loads icons from the ``assets/icons/`` directory and optionally recolours them
to match the current theme.  Icons are cached after first load.

Usage::

    from friday_ai.core.icons import Icons

    icon = Icons.get("code")                     # Default theme colour
    icon = Icons.get("close", color="#f85149")    # Custom colour
"""

from __future__ import annotations

from PyQt5.QtCore import QByteArray, QSize, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

from friday_ai.core.config import ICONS_DIR
from friday_ai.core.theme import THEME

# The placeholder colour used in our SVG source files.
_SVG_SOURCE_COLOR = "#e6edf3"


class Icons:
    """Centralized icon provider.

    All icons are loaded from ``assets/icons/``.  The ``get`` method returns
    a ``QIcon`` that can be used with any Qt widget.
    """

    _cache: dict[str, QIcon] = {}

    @classmethod
    def get(
        cls,
        name: str,
        *,
        color: str | None = None,
        size: int = 20,
    ) -> QIcon:
        """Load an icon by name, optionally recoloured.

        Parameters
        ----------
        name:
            Icon filename without extension (e.g. ``"code"``).
        color:
            Hex colour to replace the default stroke colour.  When *None*,
            the theme's ``text_secondary`` colour is used.
        size:
            Rendered pixel size (icons are SVG, so any size is sharp).
        """
        cache_key = f"{name}:{color or 'default'}:{size}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        svg_path = ICONS_DIR / f"{name}.svg"
        if not svg_path.exists():
            # Return an empty icon rather than crashing.
            return QIcon()

        svg_data = svg_path.read_text(encoding="utf-8")

        # Recolour: replace the source colour with the target colour.
        target_color = color or THEME.text_secondary
        svg_data = svg_data.replace(_SVG_SOURCE_COLOR, target_color)

        # Render SVG to a pixmap at the requested size.
        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        icon = QIcon(pixmap)
        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the icon cache (e.g. after a theme change)."""
        cls._cache.clear()

    @classmethod
    def pixmap(
        cls,
        name: str,
        *,
        color: str | None = None,
        size: int = 20,
    ) -> QPixmap:
        """Load an icon as a ``QPixmap`` instead of ``QIcon``."""
        icon = cls.get(name, color=color, size=size)
        return icon.pixmap(QSize(size, size))
