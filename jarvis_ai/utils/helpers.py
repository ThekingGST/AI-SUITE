from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def timestamp_slug() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def is_windows() -> bool:
    return sys.platform.startswith("win")


def internet_available(timeout: float = 2.0) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout).close()
        return True
    except OSError:
        return False


def safe_open_path(path: Path) -> bool:
    try:
        if is_windows():
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def iter_user_search_roots() -> Iterable[Path]:
    home = Path.home()
    names = ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music")
    for name in names:
        path = home / name
        if path.exists():
            yield path


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
