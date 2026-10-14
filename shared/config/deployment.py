"""Deployment mode detection for AI Suite."""

from __future__ import annotations

import os
import sys
from enum import Enum, auto


class DeploymentMode(Enum):
    DEVELOPMENT = auto()
    PACKAGED = auto()
    PORTABLE = auto()


def detect_deployment_mode() -> DeploymentMode:
    """Detect the current execution mode of the application."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Check if a .portable flag exists next to the executable
        executable_dir = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(executable_dir, ".portable")):
            return DeploymentMode.PORTABLE
        return DeploymentMode.PACKAGED
    
    # Check for forced mode via env var
    forced_mode = os.environ.get("AISUITE_DEPLOYMENT_MODE", "").upper()
    if forced_mode == "PACKAGED":
        return DeploymentMode.PACKAGED
    if forced_mode == "PORTABLE":
        return DeploymentMode.PORTABLE
        
    return DeploymentMode.DEVELOPMENT
