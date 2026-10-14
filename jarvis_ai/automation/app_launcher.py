from __future__ import annotations

import subprocess
import webbrowser

from utils.constants import WEB_TARGETS
from utils.helpers import internet_available
from utils.logger import LOGGER


APP_ALIASES = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "cmd": ["cmd.exe"],
    "terminal": ["wt.exe"],
    "explorer": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
}


class AppLauncher:
    def open_app(self, name: str) -> str:
        key = name.strip().lower()
        command = APP_ALIASES.get(key)
        if not command:
            return f"I do not have a launcher alias for {name} yet."
        try:
            subprocess.Popen(command, shell=False)
            return f"Opening {name}."
        except Exception as exc:
            LOGGER.warning("Open app failed: %s", exc)
            return f"I could not open {name}."

    def open_website(self, name: str) -> str:
        key = name.strip().lower()
        url = WEB_TARGETS.get(key)
        if not url:
            return f"I do not know the website {name}."
        if not internet_available():
            return "Internet connection appears unavailable."
        webbrowser.open(url)
        return f"Opening {name}."

    def play_youtube(self, query: str) -> str:
        if not internet_available():
            return "Internet connection appears unavailable."
        url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+")
        webbrowser.open(url)
        return f"Searching YouTube for {query}."
