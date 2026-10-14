"""FRIDAY entry point.

Sets up the Python path for the monorepo structure, then delegates to the
application factory.

Usage::

    python -m friday_ai.main        # From project root
    python friday_ai/main.py        # Direct execution
"""

from __future__ import annotations

import sys
from shared.config.path_manager import PathManager

# Ensure the project root is on sys.path so that fully-qualified imports
# like ``from friday_ai.core.config import CONFIG`` work correctly.
_PROJECT_ROOT = PathManager.get_bundle_dir()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def main() -> int:
    from friday_ai.app import run
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
