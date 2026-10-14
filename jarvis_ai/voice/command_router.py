from __future__ import annotations

import re
import threading
import webbrowser
from collections.abc import Callable

from ai.memory import MemoryStore
from ai.ollama_brain import OllamaBrain
from automation.app_launcher import AppLauncher
from automation.file_assistant import FileAssistant
from automation.system_control import SystemControl, close_process_by_name
from automation.utilities import Utilities
from plugins.registry import PluginCommand, PluginRegistry
from utils.helpers import normalize_text, safe_open_path
from utils.logger import LOGGER
from voice.speaker import Speaker


class CommandRouter:
    def __init__(
        self,
        brain: OllamaBrain,
        memory: MemoryStore,
        speaker: Speaker,
        on_response: Callable[[str], None] | None = None,
        on_vision_command: Callable[[str], str] | None = None,
    ) -> None:
        self.brain = brain
        self.memory = memory
        self.speaker = speaker
        self.on_response = on_response
        self.on_vision_command = on_vision_command
        self.system = SystemControl()
        self.launcher = AppLauncher()
        self.files = FileAssistant()
        self.utilities = Utilities()
        self.plugins = PluginRegistry()
        self._awaiting_rps_choice = False
        self._register_builtin_plugins()
        threading.Thread(target=self.files.refresh_index, name="JarvisFileIndexer", daemon=True).start()

    def register_plugin_command(self, command: PluginCommand) -> None:
        self.plugins.register(command)

    def _register_builtin_plugins(self) -> None:
        self.plugins.register(
            PluginCommand(
                name="system_status",
                patterns=("system status", "cpu status", "battery status"),
                handler=lambda _: self._system_status(),
                priority=10,
            )
        )
        self.plugins.register(
            PluginCommand(
                name="object_detection",
                patterns=("what do you see", "detect objects", "scan objects"),
                handler=lambda _: self.on_vision_command("objects") if self.on_vision_command else "Vision system is not attached.",
                priority=30,
            )
        )

    def handle(self, raw_text: str, speak: bool = True) -> str:
        text = normalize_text(raw_text)
        LOGGER.info("Command: %s", text)
        try:
            response = self._route(text)
        except Exception as exc:
            LOGGER.exception("Command failed")
            response = f"I encountered an error, but I recovered: {exc}"
        if self.on_response:
            self.on_response(response)
        if speak:
            self.speaker.speak(response)
        return response

    def _route(self, text: str) -> str:
        if self._awaiting_rps_choice:
            self._awaiting_rps_choice = False
            return self.utilities.rock_paper_scissors(text)

        plugin_response = self.plugins.match(text)
        if plugin_response:
            return plugin_response

        if text.startswith("open "):
            target = text.removeprefix("open ").strip()
            if target in ("youtube", "google", "whatsapp", "whatsapp web", "instagram"):
                return self.launcher.open_website(target)
            app_response = self.launcher.open_app(target)
            if "do not have" not in app_response:
                return app_response
            return self.files.open_best(target)

        if text.startswith("close "):
            return close_process_by_name(text.removeprefix("close ").strip())

        if text.startswith("find ") or text.startswith("search "):
            query = text.split(" ", 1)[1]
            matches = self.files.search(query, 5)
            if not matches:
                return f"I did not find anything matching {query}."
            return "Top matches: " + "; ".join(str(path) for path in matches[:3])

        if "latest screenshot" in text:
            path = self.files.latest_screenshot()
            if not path:
                return "I could not find a screenshot."
            safe_open_path(path)
            return f"Opening latest screenshot: {path.name}."

        if "delete temp" in text or "clean temp" in text:
            return self.files.delete_temp_files()

        if "shutdown" in text:
            return self.system.shutdown()
        if "restart" in text:
            return self.system.restart()
        if "lock" in text and "workstation" in text or text == "lock pc":
            return self.system.lock()
        if "volume up" in text:
            return self.system.set_volume_relative("up")
        if "volume down" in text:
            return self.system.set_volume_relative("down")
        if "mute" in text:
            return self.system.mute()
        if "screenshot" in text:
            return f"Screenshot saved: {self.system.screenshot()}"
        if "battery" in text or "system status" in text or "cpu" in text:
            return self._system_status()

        if "what do you see" in text or "detect objects" in text:
            if self.on_vision_command:
                return self.on_vision_command("objects")
            return "Vision system is not attached."

        if "joke" in text:
            return self.utilities.joke()
        if "quote" in text or "motivat" in text:
            return self.utilities.quote()
        if "fact" in text:
            return self.utilities.fact()
        if "coin" in text:
            return self.utilities.coin_toss()
        if "dice" in text:
            return self.utilities.dice_roll()
        if "rock paper scissors" in text:
            choice = text.replace("rock paper scissors", "").strip()
            if choice:
                return self.utilities.rock_paper_scissors(choice)
            self._awaiting_rps_choice = True
            return "Rock, paper, or scissors?"

        remember = re.match(r"remember my (.+?) is (.+)", text)
        if remember:
            key, value = remember.groups()
            self.memory.remember(key, value)
            return f"I will remember your {key} is {value}."

        recall = re.match(r"what is my (.+)", text)
        if recall:
            key = recall.group(1).strip("? ")
            value = self.memory.recall(key)
            return f"Your {key} is {value}." if value else f"I do not know your {key} yet."

        if text.startswith("play "):
            return self.launcher.play_youtube(text.removeprefix("play ").strip())
        if text.startswith("go to "):
            webbrowser.open("https://" + text.removeprefix("go to ").strip())
            return "Opening website."

        return self.brain.ask(text)

    def _system_status(self) -> str:
        status = self.system.status()
        return f"CPU {status.cpu:.0f} percent. RAM {status.ram:.0f} percent. Battery {status.battery}. WiFi {status.wifi}."
