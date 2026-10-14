"""FRIDAY application factory.

Creates and configures the QApplication instance, applies the design system
stylesheet, loads persisted workspace state, and launches the main window.
"""

from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from friday_ai.core.config import CONFIG, LOG_DIR, ensure_directories
from friday_ai.core.theme import build_stylesheet
from friday_ai.services.persistence import WorkspacePersistence
from friday_ai.ui.main_window import MainWindow
from shared.logger import get_logger

LOG = get_logger("friday", log_dir=LOG_DIR)


def create_app() -> tuple[QApplication, MainWindow]:
    """Create and configure the FRIDAY application.

    Returns
    -------
    tuple[QApplication, MainWindow]
        The Qt application instance and the main window (not yet shown).
    """
    ensure_directories()
    LOG.info("Starting FRIDAY v%s", __import__("friday_ai").__version__)

    app = QApplication(sys.argv)
    app.setApplicationName("FRIDAY")
    app.setOrganizationName("AI Suite")

    # Apply the design system
    app.setStyleSheet(build_stylesheet())

    # Load persisted workspace state
    persistence = WorkspacePersistence()
    persistence.load()

    # Create and configure the main window
    window = MainWindow(persistence=persistence)
    window.show()

    LOG.info("FRIDAY window opened: %dx%d", window.width(), window.height())
    return app, window


def run() -> int:
    """Launch FRIDAY and block until the window is closed.

    Returns
    -------
    int
        Application exit code.
    """
    app, _window = create_app()
    return app.exec()
