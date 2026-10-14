"""AI Suite Boot Screen — Design tokens, BootStage enum, and stage configuration.

This module is the single source of truth for all boot screen constants.
No milestone strings, colors, or dimensions should be hardcoded elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict

from PyQt5.QtGui import QColor, QFont


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Boot Stages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class BootStage(Enum):
    """Each stage corresponds to a real initialization block."""
    CORE         = auto()
    MEMORY       = auto()
    INTELLIGENCE = auto()
    VOICE        = auto()
    VISION       = auto()
    AUTOMATION   = auto()
    WORKSPACE    = auto()
    COMPLETE     = auto()


@dataclass(frozen=True)
class StageInfo:
    """Metadata for a single boot stage."""
    display_text: str           # Text shown in the boot message log
    reactor_level: int          # Which reactor layer activates (1-8)
    complete_text: str = ""     # Summary line shown after completion


# Ordered list of stages for iteration
BOOT_STAGE_ORDER: list[BootStage] = [
    BootStage.CORE,
    BootStage.MEMORY,
    BootStage.INTELLIGENCE,
    BootStage.VOICE,
    BootStage.VISION,
    BootStage.AUTOMATION,
    BootStage.WORKSPACE,
    BootStage.COMPLETE,
]

STAGE_CONFIG: Dict[BootStage, StageInfo] = {
    BootStage.CORE:         StageInfo("Initializing Core",            reactor_level=1, complete_text="Core Online"),
    BootStage.MEMORY:       StageInfo("Loading Memory Engine",        reactor_level=2, complete_text="Memory Online"),
    BootStage.INTELLIGENCE: StageInfo("Loading Intelligence Service", reactor_level=3, complete_text="Intelligence Online"),
    BootStage.VOICE:        StageInfo("Connecting Voice Interface",   reactor_level=4, complete_text="Voice Online"),
    BootStage.VISION:       StageInfo("Starting Vision System",       reactor_level=5, complete_text="Vision Online"),
    BootStage.AUTOMATION:   StageInfo("Loading Automation Engine",    reactor_level=6, complete_text="Automation Online"),
    BootStage.WORKSPACE:    StageInfo("Building Workspace",           reactor_level=7, complete_text="Workspace Ready"),
    BootStage.COMPLETE:     StageInfo("Systems Online",               reactor_level=8, complete_text="Systems Online"),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Color Palette
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BG_COLOR         = QColor(0, 0, 0)                  # Pure black
CYAN_PRIMARY     = QColor(0, 212, 255)              # Core neon cyan
CYAN_DIM         = QColor(0, 85, 119)               # Subtle ring outlines
CYAN_GLOW        = QColor(0, 212, 255, 38)          # Bloom / halo
WHITE_CORE       = QColor(220, 245, 255)            # Center bright white-cyan
TEXT_PRIMARY     = QColor(224, 247, 255)             # Main title text
TEXT_DIM         = QColor(74, 106, 122)              # Dimmed secondary text
TEXT_SUCCESS     = QColor(0, 212, 255)               # Checkmark / success color

# UI Effects
SHADOW_COLOR        = QColor(0, 180, 255, 40)
SHADOW_BLUR_RADIUS  = 50


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Typography
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FONT_FAMILY      = "Segoe UI Light"
FONT_FAMILY_FALLBACK = "Segoe UI"

TITLE_FONT_SIZE = 28
TITLE_LETTER_SPACING = 4.0

SUBTITLE_FONT_SIZE = 14
SUBTITLE_LETTER_SPACING = 2.0

MESSAGE_FONT_SIZE = 12
GREETING_FONT_SIZE = 14


def make_font(size: int, weight: int = QFont.Light, letter_spacing: float = 0.0) -> QFont:
    """Create a themed font with consistent settings."""
    font = QFont(FONT_FAMILY)
    if not font.exactMatch():
        font = QFont(FONT_FAMILY_FALLBACK)
    font.setPointSize(size)
    font.setWeight(weight)
    if letter_spacing > 0:
        font.setLetterSpacing(QFont.AbsoluteSpacing, letter_spacing)
    return font


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layout & Sizing
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WINDOW_WIDTH     = 900
WINDOW_HEIGHT    = 700
WINDOW_CORNER_RADIUS = 16

WINDOW_MARGIN = 40
MESSAGES_SPACING_MAIN = 8
MESSAGES_SPACING_ITEMS = 6
TITLE_BOTTOM_MARGIN = 20
GREETING_TOP_MARGIN = 15

MESSAGES_CONTAINER_MIN_WIDTH = 500
MESSAGE_ITEM_MIN_WIDTH = 300

# Reactor sizing — all relative to widget dimensions
REACTOR_SIZE     = 280      # Minimum size for the Arc Reactor widget
REACTOR_SCALE    = 0.35     # Fraction of min(width, height) used as reactor radius
PARTICLE_COUNT   = 24       # Number of orbiting particles


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Timing (milliseconds)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE1_DELAY_MS        = 300    # Black screen before reactor appears
STAGE_ANIM_DURATION_MS = 400    # Per-ring fade-in duration
GREETING_ANIM_DURATION_MS = 800 # Greeting text fade-in duration
GREETING_DELAY_MS      = 1200   # Pause after "Systems Online" before transition
TRANSITION_PULSE_MS    = 200    # Final reactor pulse duration
TRANSITION_GLOW_MS     = 1200   # Glow expansion duration
TRANSITION_WHITEOUT_MS = 400    # Window fills with light
TRANSITION_FADE_MS     = 800    # Boot window fades away
FRAME_INTERVAL_MS      = 16     # ~60 FPS paint timer
