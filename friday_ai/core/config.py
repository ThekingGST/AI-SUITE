"""FRIDAY application configuration.

All settings are defined as frozen dataclasses.  Values come from sensible
defaults and can be overridden via environment variables in a future phase.

The module-level ``CONFIG`` singleton is the single source of truth for every
configurable value in the application.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from shared.config import ConfigManager

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = ConfigManager.PROJECT_ROOT
FRIDAY_ROOT = ConfigManager.FRIDAY_ROOT
ASSETS_DIR = ConfigManager.ASSETS_DIR
ICONS_DIR = ConfigManager.ICONS_DIR
DATA_DIR = ConfigManager.DATA_DIR
LOG_DIR = ConfigManager.LOG_DIR


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WindowConfig:
    """Main window geometry and behaviour."""

    title: str = "FRIDAY AI \u2022 Software Engineer"
    width: int = 1440
    height: int = 900
    min_width: int = 960
    min_height: int = 600


@dataclass(frozen=True)
class LayoutConfig:
    """Default proportions for the three-column + bottom layout.

    Values are *ratios* used by ``QSplitter.setSizes``.  They are scaled
    to the actual window width at startup.
    """

    sidebar_width: int = 48         # Suite dock only (collapsed)
    explorer_width: int = 240       # File explorer
    editor_weight: int = 5          # Stretch factor
    workspace_panel_width: int = 340
    mission_control_height: int = 180


@dataclass(frozen=True)
class AIConfig:
    """AI backend settings (unused in Phase 1)."""

    ollama_url: str = "http://localhost:11434"
    preferred_models: tuple[str, ...] = ("llama3", "mistral", "phi")
    response_timeout: float = 60.0


@dataclass(frozen=True)
class FridayConfig:
    """Root configuration — the single source of truth."""

    window: WindowConfig = WindowConfig()
    layout: LayoutConfig = LayoutConfig()
    ai: AIConfig = AIConfig()
    openrouter_url = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ConfigManager.secrets.get_secret("OPENROUTER_API_KEY", "")
    temperature: float = 0.7
    response_timeout: float = 60.0


CONFIG = FridayConfig()


def ensure_directories() -> None:
    """Create required data directories if they don't exist."""
    for path in (DATA_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)

def ensure_directories() -> None:
    pass

