"""FRIDAY design token system and stylesheet builder.

Every colour, spacing value, font size, and border radius in the entire
application is defined here as a frozen dataclass.  The ``build_stylesheet``
function generates the complete Qt Style Sheet from these tokens.

To change the entire look-and-feel, modify the ``THEME`` singleton.  Every
component inherits its styling from this single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThemeTokens:
    """Complete visual specification for the application."""

    # ── Backgrounds ──────────────────────────────────────────────────────
    bg_base: str = "#0d1117"        # Deepest layer (window background)
    bg_surface: str = "#161b22"     # Panels, sidebars, cards
    bg_overlay: str = "#21262d"     # Elevated: tabs, dropdowns, tooltips
    bg_inset: str = "#010409"       # Recessed: editor gutter, inputs
    bg_hover: str = "#1c2128"       # Hover state for interactive elements
    bg_active: str = "#292e36"      # Active/pressed state

    # ── Borders ──────────────────────────────────────────────────────────
    border_default: str = "#30363d"
    border_muted: str = "#21262d"
    border_accent: str = "#38bdf8"

    # ── Text ─────────────────────────────────────────────────────────────
    text_primary: str = "#e6edf3"
    text_secondary: str = "#8b949e"
    text_muted: str = "#484f58"
    text_on_accent: str = "#ffffff"

    # ── Accent (FRIDAY Sky Blue) ─────────────────────────────────────────
    accent: str = "#38bdf8"
    accent_hover: str = "#7dd3fc"
    accent_emphasis: str = "#0284c7"
    accent_muted: str = "#0c4a6e"

    # ── Status ───────────────────────────────────────────────────────────
    success: str = "#3fb950"
    warning: str = "#d29922"
    danger: str = "#f85149"
    info: str = "#58a6ff"

    # ── Typography ───────────────────────────────────────────────────────
    font_family: str = "Segoe UI, system-ui, sans-serif"
    font_mono: str = "Cascadia Code, Consolas, monospace"
    font_size_xs: int = 10
    font_size_sm: int = 11
    font_size_base: int = 13
    font_size_lg: int = 15
    font_size_xl: int = 20
    font_size_title: int = 28

    # ── Spacing ──────────────────────────────────────────────────────────
    space_xs: int = 2
    space_sm: int = 4
    space_md: int = 8
    space_lg: int = 12
    space_xl: int = 16
    space_2xl: int = 24
    space_3xl: int = 32

    # ── Borders & Radius ─────────────────────────────────────────────────
    radius_sm: int = 4
    radius_md: int = 6
    radius_lg: int = 8
    radius_xl: int = 12
    border_width: int = 1

    # ── Sizing ───────────────────────────────────────────────────────────
    status_bar_height: int = 26
    tab_height: int = 36
    dock_width: int = 48
    scrollbar_width: int = 8


THEME = ThemeTokens()


# ---------------------------------------------------------------------------
# Stylesheet builder
# ---------------------------------------------------------------------------

def build_stylesheet(t: ThemeTokens | None = None) -> str:
    """Generate the complete application QSS from design tokens.

    Parameters
    ----------
    t:
        Theme tokens to use.  Defaults to the module-level ``THEME``.

    Returns
    -------
    str
        A Qt Style Sheet string ready to pass to
        ``QApplication.setStyleSheet``.
    """
    if t is None:
        t = THEME

    return f"""
/* ================================================================
   FRIDAY Design System — Auto-generated from ThemeTokens
   DO NOT EDIT — modify friday_ai/core/theme.py instead
   ================================================================ */

/* ── Global ────────────────────────────────────────────────────── */
* {{
    margin: 0;
    padding: 0;
    font-family: {t.font_family};
    font-size: {t.font_size_base}px;
    color: {t.text_primary};
    outline: none;
}}

QMainWindow {{
    background-color: {t.bg_base};
}}

QWidget {{
    background-color: transparent;
}}

/* ── Scrollbar ─────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: {t.scrollbar_width}px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t.border_default};
    min-height: 30px;
    border-radius: {t.scrollbar_width // 2}px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t.text_muted};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    height: 0;
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: {t.scrollbar_width}px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t.border_default};
    min-width: 30px;
    border-radius: {t.scrollbar_width // 2}px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t.text_muted};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    width: 0;
    background: transparent;
}}

/* ── Splitter ──────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {t.border_muted};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QSplitter::handle:hover {{
    background: {t.accent};
}}

/* ── Tooltip ───────────────────────────────────────────────────── */
QToolTip {{
    background-color: {t.bg_overlay};
    color: {t.text_primary};
    border: {t.border_width}px solid {t.border_default};
    border-radius: {t.radius_sm}px;
    padding: {t.space_sm}px {t.space_md}px;
    font-size: {t.font_size_sm}px;
}}

/* ── Labels ────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {t.text_primary};
}}

/* ── Line Edits ────────────────────────────────────────────────── */
QLineEdit {{
    background: {t.bg_inset};
    color: {t.text_primary};
    border: {t.border_width}px solid {t.border_default};
    border-radius: {t.radius_md}px;
    padding: {t.space_md}px {t.space_lg}px;
    font-size: {t.font_size_base}px;
    selection-background-color: {t.accent_muted};
}}
QLineEdit:focus {{
    border-color: {t.accent};
}}
QLineEdit::placeholder {{
    color: {t.text_muted};
}}

/* ── Text Edit (for Mission Control, code views, etc.) ─────────── */
QTextEdit, QPlainTextEdit {{
    background: {t.bg_inset};
    color: {t.text_primary};
    border: none;
    font-family: {t.font_mono};
    font-size: {t.font_size_base}px;
    selection-background-color: {t.accent_muted};
}}

/* ── Push Buttons ──────────────────────────────────────────────── */
QPushButton {{
    background-color: {t.bg_overlay};
    color: {t.text_primary};
    border: {t.border_width}px solid {t.border_default};
    border-radius: {t.radius_md}px;
    padding: {t.space_md}px {t.space_xl}px;
    font-size: {t.font_size_base}px;
}}
QPushButton:hover {{
    background-color: {t.bg_hover};
    border-color: {t.text_muted};
}}
QPushButton:pressed {{
    background-color: {t.bg_active};
}}

/* ── Tree View (File Explorer) ─────────────────────────────────── */
QTreeView {{
    background: transparent;
    border: none;
    font-size: {t.font_size_sm}px;
    color: {t.text_secondary};
}}
QTreeView::item {{
    padding: {t.space_sm}px 0;
    border-radius: {t.radius_sm}px;
}}
QTreeView::item:hover {{
    background: {t.bg_hover};
    color: {t.text_primary};
}}
QTreeView::item:selected {{
    background: {t.accent_muted};
    color: {t.text_primary};
}}
QTreeView::branch {{
    background: transparent;
}}

/* ── Custom class selectors ────────────────────────────────────── */

/* Suite Dock */
QWidget#suiteDock {{
    background-color: {t.bg_surface};
    border-right: {t.border_width}px solid {t.border_muted};
}}

/* Sidebar */
QWidget#sidebarPanel {{
    background-color: {t.bg_surface};
    border-right: {t.border_width}px solid {t.border_muted};
}}

/* Editor background */
QWidget#editorArea {{
    background-color: {t.bg_base};
}}

/* Workspace panel */
QWidget#workspacePanel {{
    background-color: {t.bg_surface};
    border-left: {t.border_width}px solid {t.border_muted};
}}

/* Mission Control */
QWidget#missionControl {{
    background-color: {t.bg_surface};
    border-top: {t.border_width}px solid {t.border_muted};
}}

/* Status bar */
QWidget#statusBar {{
    background-color: {t.accent_emphasis};
    min-height: {t.status_bar_height}px;
    max-height: {t.status_bar_height}px;
}}

/* Tab bar */
QWidget#tabBar {{
    background-color: {t.bg_surface};
    border-bottom: {t.border_width}px solid {t.border_muted};
}}

/* Welcome page */
QWidget#welcomePage {{
    background-color: {t.bg_base};
}}
"""
