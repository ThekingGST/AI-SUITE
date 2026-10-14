from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator

from ai.context_manager import ContextManager
from ai.memory import MemoryStore
from ai.personality import build_system_prompt, offline_reply
from config import CONFIG
from utils.logger import LOGGER


class OllamaBrain:
    """Local LLM brain with streaming Ollama support and an offline fallback."""

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self.context = ContextManager(CONFIG.ai.max_history_messages)
        self.context.load(memory.recent_messages(CONFIG.ai.max_history_messages))
        self.model = self._select_model()

    def _request_json(self, path: str, payload: dict | None = None, timeout: float = 4.0) -> dict:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            CONFIG.ai.ollama_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _select_model(self) -> str | None:
        try:
            data = self._request_json("/api/tags", timeout=2.0)
            installed = {m.get("name", "").split(":")[0] for m in data.get("models", [])}
            for model in CONFIG.ai.preferred_models:
                if model in installed:
                    LOGGER.info("Ollama model selected: %s", model)
                    return model
            LOGGER.warning("Ollama is running but no preferred model is installed.")
        except Exception as exc:
            LOGGER.warning("Ollama unavailable; offline fallback active: %s", exc)
        return None

    def refresh_model(self) -> str | None:
        self.model = self._select_model()
        return self.model

    def ask(self, prompt: str, on_token: Callable[[str], None] | None = None) -> str:
        self.memory.add_message("user", prompt)
        self.context.add("user", prompt)

        # Auto-retry model selection if Ollama was unavailable at startup.
        if not self.model:
            LOGGER.info("Ollama model not set; attempting auto-retry...")
            self.model = self._select_model()

        if not self.model:
            LOGGER.info("Ollama still unavailable; using offline fallback.")
            response = offline_reply(prompt)
            self._store_assistant(response)
            if on_token:
                on_token(response)
            return response

        try:
            response = "".join(self._stream_chat(prompt, on_token))
            cleaned = self._cleanup(response)
            self._store_assistant(cleaned)
            return cleaned
        except Exception as exc:
            LOGGER.warning("Ollama chat failed (%s); using fallback: %s", type(exc).__name__, exc)
            response = offline_reply(prompt)
            self._store_assistant(response)
            if on_token:
                on_token(response)
            return response

    def ask_grounded(self, prompt: str, search_context: str,
                     on_token: Callable[[str], None] | None = None) -> str:
        """Answer a user query using web search results as grounding context.

        Saves both the user message and the response to memory and context
        through the same pipeline as ``ask()``.
        """
        self.memory.add_message("user", prompt)
        self.context.add("user", prompt)

        if not self.model:
            self.model = self._select_model()
        if not self.model:
            response = offline_reply(prompt)
            self._store_assistant(response)
            return response

        grounded_prompt = (
            build_system_prompt() + "\n\n"
            "You just performed a web search. Here are the results:\n"
            f"{search_context}\n\n"
            "INSTRUCTIONS:\n"
            "1. Synthesize these results to answer the user's question accurately.\n"
            "2. Answer NATURALLY and CONVERSATIONALLY in your JARVIS persona.\n"
            "3. Do NOT say 'Based on the web results' or 'According to the search'. "
            "Just state the facts as if you already know them.\n"
            "4. If the results are news, summarize them nicely. "
            "If they don't contain the answer, say you aren't sure right now.\n"
            "5. Keep the response concise but informative.\n"
        )

        messages = [
            {"role": "system", "content": grounded_prompt},
            *self.context.messages(),
        ]
        payload = {"model": self.model, "messages": messages, "stream": False}

        try:
            res = self._request_json("/api/chat", payload, timeout=CONFIG.ai.response_timeout_seconds)
            reply = res.get("message", {}).get("content", "").strip()
            cleaned = self._cleanup(reply)
            self._store_assistant(cleaned)
            return cleaned
        except Exception as exc:
            LOGGER.warning("Grounded ask failed (%s): %s", type(exc).__name__, exc)
            response = offline_reply(prompt)
            self._store_assistant(response)
            return response

    def _stream_chat(self, prompt: str, on_token: Callable[[str], None] | None) -> Iterator[str]:
        messages = [{"role": "system", "content": build_system_prompt()}, *self.context.messages()]
        payload = {"model": self.model, "messages": messages, "stream": True}
        req = urllib.request.Request(
            CONFIG.ai.ollama_url + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=CONFIG.ai.response_timeout_seconds) as response:
            for line in response:
                if not line.strip():
                    continue
                data = json.loads(line.decode("utf-8"))
                token = data.get("message", {}).get("content", "")
                if token:
                    if on_token:
                        on_token(token)
                    yield token
                if data.get("done"):
                    break

    def _store_assistant(self, response: str) -> None:
        self.context.add("assistant", response)
        self.memory.add_message("assistant", response)

    @staticmethod
    def _cleanup(text: str) -> str:
        return text.strip().replace("\x00", "")
