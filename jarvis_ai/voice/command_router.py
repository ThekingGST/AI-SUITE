from __future__ import annotations

import re
import threading
import webbrowser
from collections.abc import Callable

from jarvis_ai.ai.memory import MemoryStore
from jarvis_ai.ai.ollama_brain import OllamaBrain
from jarvis_ai.ai.openrouter_brain import OpenRouterBrain
from jarvis_ai.automation.app_launcher import AppLauncher
from shared.documents.generators import GeneratorManager
from jarvis_ai.automation.brightness_controller import BrightnessController
from jarvis_ai.automation.file_assistant import FileAssistant
from jarvis_ai.automation.folder_launcher import FolderLauncher
from jarvis_ai.automation.system_control import SystemControl, close_process_by_name
from jarvis_ai.automation.utilities import Utilities
from jarvis_ai.automation.volume_controller import VolumeController
from jarvis_ai.automation.web_search import WebSearch
from jarvis_ai.config import CONFIG
from jarvis_ai.plugins.registry import PluginCommand, PluginRegistry
from jarvis_ai.utils.helpers import normalize_text, safe_open_path
from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.speaker import Speaker


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
        brain: OllamaBrain | OpenRouterBrain,
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
        self.generator_manager = GeneratorManager()
        self.utilities = Utilities()
        self.web_search = WebSearch()
        self.plugins = PluginRegistry()
        self._awaiting_rps_choice = False
        self.last_automation_target = ""
        self._register_builtin_plugins()
        threading.Thread(target=self.files.refresh_index, name="JarvisFileIndexer", daemon=True).start()

    def register_plugin_command(self, command: PluginCommand) -> None:
        self.plugins.register(command)

    def _register_builtin_plugins(self) -> None:
        self.plugins.register(
            PluginCommand(
                name="system_status",
                patterns=("system status", "cpu status", "battery status", "how is my laptop", "how is my computer", "any problems", "how is my system", "is anything wrong"),
                handler=lambda _: self._intelligence_status(),
                priority=10,
            )
        )
        self.plugins.register(
            PluginCommand(
                name="jarvis_status",
                patterns=("how is jarvis", "jarvis status", "is jarvis working"),
                handler=lambda _: self._jarvis_status(),
                priority=10,
            )
        )
        self.plugins.register(
            PluginCommand(
                name="ollama_status",
                patterns=("is ollama working", "ollama status"),
                handler=lambda _: self._ollama_status(),
                priority=10,
            )
        )
        self.plugins.register(
            PluginCommand(
                name="project_status",
                patterns=("how is my project", "how is the jarvis project", "project status"),
                handler=lambda _: self._project_status(),
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
        import time
        import threading
        t_start = time.perf_counter()
        LOGGER.info("Routing command: '%s'", raw_text)
        LOGGER.info("[DOC] query received")
        
        text = self._normalize_command(raw_text)
        
        if text in ("stop", "cancel", "never mind"):
            speech_manager = getattr(self.speaker, "manager", None)
            if speech_manager:
                speech_manager.interrupt()
            return ""

        t0 = time.perf_counter()
        try:
            result = self._route(text)
        except Exception as exc:
            LOGGER.exception("Command failed")
            result = f"I encountered an error, but I recovered: {exc}"
        t_route = (time.perf_counter() - t0) * 1000
        LOGGER.info("[TIMING] Router intent/planning: %.2f ms", t_route)

        from typing import Iterator
        if isinstance(result, Iterator) or hasattr(result, "__iter__") and not isinstance(result, str):
            # It's a stream of tokens from the LLM
            from jarvis_ai.voice.v2.sentence_buffer import SentenceBuffer
            from jarvis_ai.voice.v2.types import SpeechPriority

            speech_manager = getattr(self.speaker, "manager", None)
            
            # Check if this might be a generation task based on user input
            is_generation_task = re.search(r"\b(create|generate|save|export|make)\b.*\b(file|pdf|word|docx|excel|xlsx|csv|text|txt|markdown|md|json|powerpoint|pptx|presentation)\b", text.lower()) is not None
            
            if speech_manager and speak and not is_generation_task:
                speech_manager.set_streaming_session(True)
            
            def enqueue_chunk(chunk: str) -> None:
                if speech_manager and speak and not is_generation_task:
                    speech_manager.enqueue(chunk, SpeechPriority.NORMAL)

            buffer = SentenceBuffer(on_sentence=enqueue_chunk)
            
            full_response_parts = []
            for token in result:
                if speech_manager and speech_manager.is_aborted:
                    LOGGER.info("CommandRouter: LLM generation aborted.")
                    break
                full_response_parts.append(token)
                if not is_generation_task:
                    buffer.feed(token)
                
            if not (speech_manager and speech_manager.is_aborted) and not is_generation_task:
                buffer.flush()
            else:
                buffer.clear()
                
            full_response = "".join(full_response_parts)
            
            if full_response.strip() == "":
                LOGGER.warning("[LLM] Empty response received. Applying safe fallback response.")
                fallback = "Sorry, I wasn't able to generate a response this time. Please try again."
                
                # Check for failed documents if applicable
                if hasattr(self, "brain") and hasattr(self.brain, "retriever") and self.brain.retriever:
                    store = self.brain.retriever.store
                    if store and store.documents:
                        for doc in store.documents.values():
                            if getattr(doc, 'failed', False):
                                fallback = f"Sorry, Captain. I couldn't extract readable content from {doc.filename}. It may be scanned, protected, corrupted, or contain content this parser can't read yet."
                                break
                                
                full_response = fallback
                if speech_manager and speak:
                    speech_manager.enqueue(full_response, SpeechPriority.NORMAL)
            
            # Handle File Generation
            if "[GENERATE_FILE:" in full_response:
                match = re.search(r"\[GENERATE_FILE:\s*(.+?)\](.*)", full_response, re.DOTALL)
                if match:
                    filename = match.group(1).strip()
                    file_content = match.group(2).strip()
                    ext = ""
                    if "." in filename:
                        parts = filename.rsplit(".", 1)
                        ext = "." + parts[1]
                        filename = parts[0]
                        
                    try:
                        out_path = self.generator_manager.generate_file(file_content, filename, ext)
                        success_msg = f"I have generated the file: {out_path.name}."
                        full_response = success_msg
                        if speech_manager and speak:
                            speech_manager.enqueue(success_msg, SpeechPriority.NORMAL)
                    except Exception as e:
                        LOGGER.exception("Failed to generate file")
                        full_response = f"I tried to generate the file, but encountered an error: {e}"
                        if speech_manager and speak:
                            speech_manager.enqueue(full_response, SpeechPriority.NORMAL)
            
            if speech_manager and speak and not is_generation_task:
                speech_manager.set_streaming_session(False)
            
            if self.on_response:
                self.on_response(full_response)
                
            return full_response
        else:
            # It's a standard string response (automation, error, fallback)
            if self.on_response:
                self.on_response(result)
            if speak:
                self.speaker.speak(result)
            return result

    def _route(self, text: str) -> str | Iterator[str]:
        if self._awaiting_rps_choice:
            self._awaiting_rps_choice = False
            return self.utilities.rock_paper_scissors(text)
            
        automation_verbs = ("open ", "launch ", "close ", "search ", "play ", "increase ", "decrease ", "mute ", "maximize ", "minimize ", "find ")
        if " and " in text and any(text.startswith(v) for v in automation_verbs):
            parts = text.split(" and ", 1)
            if any(parts[1].startswith(v) for v in automation_verbs):
                res1 = self._route(parts[0])
                res2 = self._route(parts[1])
                s1 = res1 if isinstance(res1, str) else "".join(list(res1))
                s2 = res2 if isinstance(res2, str) else "".join(list(res2))
                return f"{s1} {s2}".strip()

        # Context resolution
        if self.last_automation_target and re.search(r'\b(it|that)\b', text, re.IGNORECASE):
            text = re.sub(r'\b(it|that)\b', self.last_automation_target, text, flags=re.IGNORECASE)
            LOGGER.info("Resolved context 'it'/'that' to: %s", self.last_automation_target)

        # 2. Automation
        sys_res = self._route_system_automation(text)
        if sys_res:
            LOGGER.info("Intent: System Automation | Confidence: 1.00")
            return sys_res

        if "lock pc" in text or "lock my pc" in text or "lock computer" in text:
            LOGGER.info("Intent: Automation | Confidence: 1.00")
            return self.system.lock()
        if "screenshot" in text:
            LOGGER.info("Intent: Automation | Confidence: 1.00")
            return f"Screenshot saved: {self.system.screenshot()}"

        if text.startswith("open "):
            LOGGER.info("Intent: Automation | Confidence: 1.00")
            target = text.removeprefix("open ").strip()
            self.last_automation_target = target
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
            target = text.removeprefix("close ").strip()
            self.last_automation_target = target
            return close_process_by_name(target)

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

        # Explicit Memory Commands
        remember = re.match(r"(?:please )?remember (?:that )?(.*)", text)
        if remember:
            content = remember.group(1).strip()
            self.memory.remember(content)
            return f"I will remember that {content}."
            
        forget = re.match(r"(?:please )?forget (?:that )?(.*)", text)
        if forget:
            content = forget.group(1).strip()
            success = self.memory.forget(content)
            if success:
                return f"I have forgotten the information regarding: {content}."
            else:
                return f"I couldn't find any memory matching: {content}."

        if "what do you remember about me" in text or "what are my preferences" in text:
            mems = self.memory.list_memories()
            if not mems:
                return "I don't have any saved preferences or memories about you yet."
            return "Here is what I remember:\n" + "\n".join(f"- {m}" for m in mems)

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

        # 3. Internal AI Entities
        lowered_text = text.lower()
        if any(entity in lowered_text for entity in ("jarvis", "friday", "edith", "ai suite")):
            LOGGER.info("Intent: Internal Entity | Confidence: 1.00")
            if "open friday" in lowered_text or "launch friday" in lowered_text:
                pass 
                     
            if "is friday running" in lowered_text:
                return "Yes, Friday is currently running as a background workspace within AI Suite."
            if "where is friday" in lowered_text:
                return "Friday is installed in the AI Suite workspace directory."
            if "update friday" in lowered_text:
                return "Routing to development updater for Friday."
            
            return self._internal_entity_status(text)

        # 4. System Intelligence
        if any(kw in lowered_text for kw in ("battery", "system status", "cpu", "gpu", "disk", "ram", "laptop")):
            LOGGER.info("Intent: Intelligence | Confidence: 1.00")
            return self._intelligence_status()

        # 5. Web Search
        search_plan = self._plan_search(text)
        if search_plan and search_plan.get("needs_search"):
            LOGGER.info("Intent: Web Search | Confidence: 0.98")
            query = search_plan.get("search_query") or text
            return self._handle_search(text, query)

        # 6. General Conversation
        LOGGER.info("Intent: General Conversation | Confidence: 0.85")
        LOGGER.info("[ROUTER] route = local_ai")
        return self.brain.ask_stream(text)

    def _plan_search(self, text: str) -> dict | None:
        """Ask the LLM whether a web search is needed, with conversation context."""
        if not self.brain.model:
            return None
            
        local_keywords = ["laptop", "system status", "pc", "battery", "cpu", "jarvis", "project", "ollama"]
        if any(kw in text.lower() for kw in local_keywords):
            return {"needs_search": False, "search_query": None}

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
            "about time/date, asking about the assistant's capabilities, or asking about attached files/documents (e.g. 'summarize this pdf', 'what is in this presentation').\n\n"
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

    def _handle_search(self, text: str, search_query: str) -> str | Iterator[str]:
        """Perform a web search and pass results through the brain's grounded pipeline."""
        results = self.web_search.search(search_query)
        if not results:
            LOGGER.info("[ROUTER] route = local_ai")
        return self.brain.ask_stream(text)

        context = "\n".join(f"- {r}" for r in results)
        return self.brain.ask_grounded_stream(text, context)

    def _system_status(self) -> str:
        status = self.system.status()
        return f"CPU {status.cpu:.0f} percent. RAM {status.ram:.0f} percent. Battery {status.battery}. WiFi {status.wifi}."

    def _intelligence_status(self) -> str | Iterator[str]:
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        intel = ServiceContainer.get(IntelligenceService)
        if not intel:
            return self._system_status()
            
        reports = intel.inspect_all()
        hw_reports = [r for r in reports if r.inspector in ("cpu", "memory", "battery", "gpu", "disk", "network", "windows")]
        
        context_parts = []
        for r in hw_reports:
            context_parts.append(f"{r.inspector.upper()}\n{r.summary}\n{r.details}")
        context = "\n\n".join(context_parts)
        
        instruction = (
            "Use ONLY the supplied InspectionReports below.\n"
            "Never infer.\n"
            "Never estimate.\n"
            "Never guess.\n"
            "Never use prior knowledge.\n"
            "If information is unavailable, explicitly say it is unavailable.\n\n"
            "InspectionReports:\n"
            f"{context}\n\n"
            "Now, explain these system inspection results naturally to the user."
        )
        return self.brain.ask_grounded_stream("Tell me about my system hardware.", context, instruction=instruction)

    def _internal_entity_status(self, text: str) -> str | Iterator[str]:
        lowered = text.lower()
        context = ""
        
        if "jarvis" in lowered:
            context = (
                "Entity: JARVIS\n"
                "Purpose: Primary Voice Assistant and System Controller\n"
                "Capabilities: System control, intelligence routing, web search, conversational AI\n"
                "Architecture: Ollama-backed LLM with V2 Audio Pipeline and Event Bus integration\n"
            )
        elif "friday" in lowered:
            context = (
                "Entity: FRIDAY\n"
                "Purpose: AI-powered Development IDE\n"
                "Capabilities: Codebase management, toolchain discovery, terminal automation\n"
                "Architecture: PyQt5 GUI embedded inside AI Suite\n"
            )
        elif "edith" in lowered:
            context = (
                "Entity: EDITH\n"
                "Purpose: Security, Networking, and Infrastructure Monitor\n"
                "Capabilities: Network scanning, port monitoring, threat detection\n"
                "Architecture: Autonomous background service within AI Suite\n"
            )
        elif "ai suite" in lowered:
            context = (
                "Entity: AI Suite\n"
                "Purpose: Master orchestration platform\n"
                "Capabilities: Manages Jarvis, Friday, and Edith workspaces, handles shared memory and LLM resources\n"
                "Architecture: Event-driven singleton architecture with QMainWindow\n"
            )
            
        if not context:
            # Fallback if somehow it reached here but didn't match exactly
            context = "Entity: Unknown internal AI entity."

        instruction = (
            "You are answering a question about one of your internal AI Suite modules/personas.\n"
            "Use the provided structured context below to answer the user's question NATURALLY and CONVERSATIONALLY.\n"
            "Do NOT perform a web search.\n"
            "Do NOT make up features that are not listed.\n\n"
            f"{context}"
        )
        return self.brain.ask_grounded_stream(text, context, instruction=instruction)

    def _jarvis_status(self) -> str | Iterator[str]:
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        intel = ServiceContainer.get(IntelligenceService)
        if not intel:
            return "Intelligence service is not running."
            
        report = intel.inspect("jarvis")
        if not report:
            return "JARVIS internal inspection failed."
        prompt = f"Explain JARVIS's internal status naturally based on this inspection:\n{report.summary}\nDetails: {report.details}"
        return self.brain.ask_grounded_stream(prompt, "")

    def _ollama_status(self) -> str:
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        intel = ServiceContainer.get(IntelligenceService)
        if not intel:
            return "Intelligence service is not running."
            
        report = intel.inspect("ollama")
        if not report:
            return "Ollama inspection failed."
        return report.summary

    def _project_status(self) -> str | Iterator[str]:
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        import os
        intel = ServiceContainer.get(IntelligenceService)
        if not intel:
            return "Intelligence service is not running."
            
        from shared.config import ConfigManager
        repo_path = str(ConfigManager.PROJECT_ROOT)
        git_rep = intel.inspect("git", repo_path=repo_path)
        proj_rep = intel.inspect("project", project_path=repo_path)
        
        context = f"Git: {git_rep.summary}\nProject: {proj_rep.summary}"
        prompt = f"Explain the project status naturally based on this live inspection:\n{context}"
        return self.brain.ask_grounded_stream(prompt, "")

    def _route_system_automation(self, text: str) -> str | None:
        percent = self._extract_percent(text)
        if "volume" in text:
            self.last_automation_target = "volume"
            if percent is not None:
                return self.volume.set_volume(percent)
            if "up" in text or "increase" in text or "raise" in text:
                return self.volume.change_volume(10)
            if "down" in text or "decrease" in text or "lower" in text:
                return self.volume.change_volume(-10)
        if text in ("stop", "cancel", "shut up", "be quiet", "silence"):
            self.speaker.interrupt()
            return "Speech interrupted."

        if text in ("mute", "mute jarvis", "mute voice"):
            self.speaker.set_enabled(False)
            return "Voice muted."
        
        if text in ("unmute", "unmute jarvis", "unmute voice"):
            self.speaker.set_enabled(True)
            return "Voice unmuted."

        if text in ("mute system", "mute audio") or "mute system" in text or "mute audio" in text:
            return self.volume.mute()
        if text in ("unmute system", "unmute audio") or "unmute system" in text or "unmute audio" in text:
            return self.volume.unmute()

        if "brightness" in text:
            self.last_automation_target = "brightness"
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
