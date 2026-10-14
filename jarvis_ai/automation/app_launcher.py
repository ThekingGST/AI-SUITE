from __future__ import annotations

import os
import subprocess
import webbrowser

from jarvis_ai.utils.constants import WEB_TARGETS
from jarvis_ai.utils.helpers import internet_available
from jarvis_ai.utils.logger import LOGGER


import shutil

APP_ALIASES = {
    "terminal": "wt.exe",
    "task manager": "taskmgr.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "explorer": "explorer.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    "copilot": "ms-copilot://",
    "settings": "ms-settings:",
}

import sys
from shared.config import PathManager

def _get_workspace_command(workspace_name: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--workspace", workspace_name]
    else:
        main_py = str(PathManager.get_bundle_dir() / "ai_suite" / "main.py")
        return [sys.executable, main_py, "--workspace", workspace_name]

APP_ALIASES["friday"] = _get_workspace_command("friday")
APP_ALIASES["jarvis"] = _get_workspace_command("jarvis")
APP_ALIASES["edith"] = _get_workspace_command("edith")


import random

def _random_confirm(action: str, target: str) -> str:
    choices = [
        f"Sure. {action} {target}.",
        f"Done.",
        f"On it.",
        f"{action} {target} now.",
        f"I'm {action.lower()} {target} for you."
    ]
    return random.choice(choices)

class AppLauncher:
    def open_app(self, name: str) -> str:
        key = name.strip().lower()
        target = APP_ALIASES.get(key)
        
        if not target:
            return f"I do not have a launcher alias for {name} yet."
            
        try:
            if isinstance(target, list):
                subprocess.Popen(target, shell=False, creationflags=0x08000000)
                return _random_confirm("Opening", name)
                
            if target.startswith("ms-") or "://" in target:
                os.startfile(target)
                return _random_confirm("Opening", name)
                
            exe_path = shutil.which(target)
            if exe_path:
                subprocess.Popen([exe_path], shell=False, creationflags=0x08000000)
            else:
                os.startfile(target)
            return _random_confirm("Opening", name)
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
        return _random_confirm("Opening", name)

    def play_youtube(self, query: str) -> str:
        if not internet_available():
            return "Internet connection appears unavailable."
        url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+")
        webbrowser.open(url)
        return _random_confirm("Searching YouTube for", query)
