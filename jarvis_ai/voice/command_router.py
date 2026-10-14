from __future__ import annotations

import re
import threading
import webbrowser
from collections.abc import Callable

from ai.memory import MemoryStore
from ai.ollama_brain import OllamaBrain
from automation.app_launcher import AppLauncher
from automation.brightness_controller import BrightnessController
from automation.file_assistant import FileAssistant
from automation.folder_launcher import FolderLauncher
from automation.system_control import SystemControl, close_process_by_name
from automation.utilities import Utilities
from automation.volume_controller import VolumeController
from automation.web_search import WebSearch
from config import CONFIG
from plugins.registry import PluginCommand, PluginRegistry
from utils.helpers import normalize_text, safe_open_path
from utils.logger import LOGGER
from voice.speaker import Speaker


class CommandRouter:
    COMMON_FIXES = {
        "vloume": "volume",
        "volum": "volume",
        "bread mess": "brightness",
        "bride mess": "brightness",
        "bright mess": "brightness",
        "volume two ": "volume to ",
        "brightness two ": "brightness to ",
    }
    NUMBER_WORDS = {
        "zero": 0,
        "ten": 10,
        "twenty": 20,
        "thirty": 30,
        "forty": 40,
        "fifty": 50,
        "sixty": 60,
        "seventy": 70,
        "eighty": 80,
        "ninety": 90,
        "hundred": 100,
    }

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
        self.volume = VolumeController()
        self.brightness = BrightnessController()
        self.launcher = AppLauncher()
        self.folders = FolderLauncher()
        self.files = FileAssistant()
        self.utilities = Utilities()
        self.web_search = WebSearch()
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
        text = self._normalize_command(raw_text)
        print("NORMALIZED:", text)
        LOGGER.info("NORMALIZED: %s", text)
        LOGGER.info("Command: %s", text)
        try:
            response = self._route(text)
        except Exception as exc:
            LOGGER.exception("Command failed")
            response = f"I encountered an error, but I recovered: {exc}"
        if self.on_response:
            self.on_response(response)
        if speak:
            print("DEBUG TTS:", response)
            self.speaker.speak(response)
        return response

    def _route(self, text: str) -> str:
        if self._awaiting_rps_choice:
            self._awaiting_rps_choice = False
            return self.utilities.rock_paper_scissors(text)

        system_response = self._route_system_automation(text)
        if system_response:
            return system_response

        if text.startswith("open "):
            target = text.removeprefix("open ").strip()
            folder_response = self.folders.open_folder(target)
            if folder_response:
                return folder_response
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

        if (
            "what do you see" in text
            or "what can you see" in text
            or "what do you detect" in text
            or "detect objects" in text
            or "what can you detect" in text
            or "what objects are visible" in text
            or "objects visible" in text
            or "what is in front of you" in text
        ):
            if self.on_vision_command:
                return self.on_vision_command("objects")
            return "Vision system is not attached."

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

        # Entertainment — only match short, direct requests to avoid false positives
        # like "facts about quantum computing" or "is this a joke"
        words = text.split()
        if "joke" in text and len(words) <= 6 and "about" not in text:
            return self.utilities.joke()
        if ("quote" in text or "motivat" in text) and len(words) <= 6:
            return self.utilities.quote()
        if "fact" in text and len(words) <= 6 and "about" not in text:
            return self.utilities.fact()
        if "coin" in text and len(words) <= 4:
            return self.utilities.coin_toss()
        if "dice" in text and len(words) <= 4:
            return self.utilities.dice_roll()
        if "rock paper scissors" in text:
            choice = text.replace("rock paper scissors", "").strip()
            if choice:
                return self.utilities.rock_paper_scissors(choice)
            self._awaiting_rps_choice = True
            return "Rock, paper, or scissors?"

        plugin_response = self.plugins.match(text)
        if plugin_response:
            return plugin_response

        if text.startswith("play "):
            return self.launcher.play_youtube(text.removeprefix("play ").strip())
        if text.startswith("go to "):
            webbrowser.open("https://" + text.removeprefix("go to ").strip())
            return "Opening website."

        # Classify if web search is needed
        search_plan = self._plan_search(text)
        if search_plan and search_plan.get("needs_search"):
            query = search_plan.get("search_query") or text
            return self._handle_search(text, query)

        return self.brain.ask(text)

    def _plan_search(self, text: str) -> dict | None:
        """Ask the LLM whether a web search is needed, with conversation context."""
        if not self.brain.model:
            return None

        # Include recent conversation so the LLM can resolve follow-ups
        recent = self.brain.context.summary_for_planner()
        context_block = f"\nRecent conversation:\n{recent}\n" if recent else ""

        prompt = (
            "You are an intent classifier. Decide whether the user's query requires "
            "a web search for real-time information, latest news, current events, or "
            "specific factual details about entities (people, places, companies, "
            "organizations).\n\n"
            "NO search needed for: greetings, general conversation, follow-ups that "
            "only rephrase or summarize previous answers, basic coding/math, asking "
            "about time/date, or asking about the assistant's capabilities.\n\n"
            "YES search needed for: questions about specific people, places, "
            "organizations, current events, latest news, or follow-ups that reference "
            "a topic requiring NEW factual information (e.g., 'tell me more about him' "
            "after discussing a person).\n\n"
            "If search IS needed and the query is a follow-up, resolve any pronouns "
            "or references using the conversation history and generate a complete, "
            "self-contained search query.\n"
            f"{context_block}"
            f"\nCurrent user query: '{text}'\n\n"
            "Output ONLY a JSON object with exactly two keys:\n"
            '1. "needs_search": boolean\n'
            '2. "search_query": string (optimized search query) or null\n'
        )
        payload = {
            "model": self.brain.model,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
        }
        try:
            res = self.brain._request_json("/api/chat", payload, timeout=CONFIG.ai.response_timeout_seconds)
            reply = res.get("message", {}).get("content", "").strip()
            import json
            plan = json.loads(reply)
            LOGGER.info("Search plan: %s", plan)
            return plan
        except Exception as e:
            LOGGER.error("Search planning failed: %s", e)
            return None

    def _handle_search(self, text: str, search_query: str) -> str:
        """Perform a web search and pass results through the brain's grounded pipeline."""
        results = self.web_search.search(search_query)
        if not results:
            return self.brain.ask(text)

        context = "\n".join(f"- {r}" for r in results)
        return self.brain.ask_grounded(text, context)

    def _system_status(self) -> str:
        status = self.system.status()
        return f"CPU {status.cpu:.0f} percent. RAM {status.ram:.0f} percent. Battery {status.battery}. WiFi {status.wifi}."

    def _route_system_automation(self, text: str) -> str | None:
        percent = self._extract_percent(text)
        if "volume" in text:
            if percent is not None:
                return self.volume.set_volume(percent)
            if "up" in text or "increase" in text or "raise" in text:
                return self.volume.change_volume(10)
            if "down" in text or "decrease" in text or "lower" in text:
                return self.volume.change_volume(-10)
        if text in ("mute", "mute system", "mute audio") or "mute system" in text or "mute audio" in text:
            return self.volume.mute()
        if text in ("unmute", "unmute system", "unmute audio") or "unmute system" in text or "unmute audio" in text:
            return self.volume.unmute()

        if "brightness" in text:
            if percent is not None and ("set" in text or "to" in text):
                return self.brightness.set_brightness(percent)
            if "up" in text or "increase" in text or "raise" in text:
                return self.brightness.change_brightness(10)
            if "down" in text or "decrease" in text or "lower" in text:
                return self.brightness.change_brightness(-10)

        if "shutdown" in text:
            return self.system.shutdown()
        if "restart" in text:
            return self.system.restart()
        if ("lock" in text and "workstation" in text) or text == "lock pc":
            return self.system.lock()
        if "screenshot" in text:
            return f"Screenshot saved: {self.system.screenshot()}"
        if "battery" in text or "system status" in text or "cpu" in text:
            return self._system_status()
        return None

    @staticmethod
    def _extract_percent(text: str) -> int | None:
        match = re.search(r"(\d{1,3})\s*(?:percent|%)?", text)
        if not match:
            return None
        return max(0, min(100, int(match.group(1))))

    def _normalize_command(self, text: str) -> str:
        normalized = normalize_text(text)
        for wrong, right in self.COMMON_FIXES.items():
            normalized = re.sub(rf"\b{re.escape(wrong)}\b", right, normalized)
        for word, number in self.NUMBER_WORDS.items():
            normalized = re.sub(rf"\b{word}\b", str(number), normalized)
        return normalized
