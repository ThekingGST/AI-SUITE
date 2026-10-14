from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator

from jarvis_ai.ai.context_manager import ContextManager
from jarvis_ai.ai.memory import MemoryStore
from jarvis_ai.ai.personality import build_system_prompt, offline_reply
from jarvis_ai.config import CONFIG
from shared.documents.context import Retriever
from jarvis_ai.utils.logger import LOGGER


class OllamaBrain:
    """Local LLM brain using direct HTTP requests to Ollama API."""

    def __init__(self, memory: MemoryStore, retriever: Retriever = None) -> None:
        self.retriever = retriever
        self.memory = memory
        self.context = ContextManager(CONFIG.ai.max_history_messages)
        self.context.load(memory.recent_messages(CONFIG.ai.max_history_messages))
        self.model = self._detect_model()
        if self.model:
            LOGGER.info("OllamaBrain initialized with model: %s", self.model)
        else:
            LOGGER.warning("OllamaBrain initialized, but no local model was found. Falling back to offline mode.")

    def refresh_model(self) -> str | None:
        self.model = self._detect_model()
        return self.model

    def ask(self, prompt: str, on_token: Callable[[str], None] | None = None) -> str:
        tokens = []
        for token in self.ask_stream(prompt):
            tokens.append(token)
            if on_token:
                on_token(token)
        return "".join(tokens)

    def ask_stream(self, prompt: str, language: str | None = None) -> Iterator[str]:
        import time
        t_start = time.perf_counter()
        LOGGER.info("[BRAIN] ask_stream started")
        LOGGER.info("[LLM] Language: %s", language or "English")
        
        if not self.model:
            reply = offline_reply(prompt)
            self._store_assistant(reply)
            yield reply
            return

        self.memory.add_message("user", prompt)
        self.context.add("user", prompt)
        
        sys_prompt = build_system_prompt()
        if language and language.lower() not in ("english", "en"):
            sys_prompt += f"\n\nIMPORTANT: You MUST respond to the user in {language}. Do NOT respond in English."
        
        # Inject relevant active long-term memories
        t0 = time.perf_counter()
        relevant_memories = self.memory.search_memories(prompt, limit=5)
        t_mem = (time.perf_counter() - t0) * 1000
        LOGGER.info("[TIMING] Memory search: %.2f ms", t_mem)
        
        if relevant_memories:
            memory_context = "Relevant memories from past conversations:\n" + "\n".join([f"- {m}" for m in relevant_memories])
            sys_prompt = sys_prompt + "\n\n" + memory_context
            
        t0 = time.perf_counter()
        if self.retriever:
            doc_context = self.retriever.retrieve(prompt)
            if doc_context:
                sys_prompt = sys_prompt + "\n\n" + doc_context
        t_doc = (time.perf_counter() - t0) * 1000
        LOGGER.info("[TIMING] Document search: %.2f ms", t_doc)
                
        messages = [{"role": "system", "content": sys_prompt}, *self.context.messages()]
        LOGGER.info("[LLM] Prompt prepared")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"num_ctx": 8192},
        }

        full_response = []
        try:
            req = urllib.request.Request(
                f"{CONFIG.ai.ollama_url}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            t0 = time.perf_counter()
            LOGGER.info("[LLM] Connection established")
            with urllib.request.urlopen(req, timeout=CONFIG.ai.response_timeout_seconds) as response:
                t_conn = (time.perf_counter() - t0) * 1000
                LOGGER.info("[TIMING] LLM connection: %.2f ms", t_conn)
                
                first_token = True
                for line in response:
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                        token = data.get("message", {}).get("content", "")
                        if token:
                            if first_token:
                                t_ttft = (time.perf_counter() - t0) * 1000
                                LOGGER.info("[LLM] First token received")
                                LOGGER.info("[TIMING] Time to first token: %.2f ms", t_ttft)
                                first_token = False
                            full_response.append(token)
                            LOGGER.info("[BRAIN] chunk received"); yield token
                    except json.JSONDecodeError:
                        continue
            t_gen = (time.perf_counter() - t0) * 1000
            LOGGER.info("[LLM] Stream completed")
            LOGGER.info("[TIMING] Total LLM generation: %.2f ms", t_gen)
            LOGGER.info("[LLM] Total response length: %d", len("".join(full_response)))
        except (urllib.error.URLError, TimeoutError) as exc:
            LOGGER.error("Ollama inference failed: %s", exc)
            yield offline_reply(prompt)
            return

        cleaned = self._cleanup("".join(full_response))
        self._store_assistant(cleaned)

    def ask_grounded(self, prompt: str, search_context: str,
                     on_token: Callable[[str], None] | None = None) -> str:
        tokens = []
        for token in self.ask_grounded_stream(prompt, search_context):
            tokens.append(token)
            if on_token:
                on_token(token)
        return "".join(tokens)

    def ask_grounded_stream(self, prompt: str, search_context: str, instruction: str = None, language: str | None = None) -> Iterator[str]:
        LOGGER.info("[LLM] Grounded request started")
        LOGGER.info("[LLM] Language: %s", language or "English")
        if not self.model:
            reply = offline_reply(prompt)
            self._store_assistant(reply)
            yield reply
            return

        self.memory.add_message("user", prompt)
        self.context.add("user", prompt)

        if instruction is None:
            instruction = (
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

        sys_prompt = build_system_prompt()
        if language and language.lower() not in ("english", "en"):
            sys_prompt += f"\n\nIMPORTANT: You MUST respond to the user in {language}. Do NOT respond in English."

        grounded_prompt = (
            sys_prompt + "\n\n"
            f"{instruction}\n\n"
        )

        messages = [
            {"role": "system", "content": grounded_prompt},
            *self.context.messages(),
        ]
        LOGGER.info("[LLM] Grounded prompt prepared")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"num_ctx": 8192},
        }

        full_response = []
        try:
            req = urllib.request.Request(
                f"{CONFIG.ai.ollama_url}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            LOGGER.info("[LLM] Connection established")
            with urllib.request.urlopen(req, timeout=CONFIG.ai.response_timeout_seconds) as response:
                first_token = True
                for line in response:
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                        token = data.get("message", {}).get("content", "")
                        if token:
                            if first_token:
                                LOGGER.info("[LLM] First token received")
                                first_token = False
                            full_response.append(token)
                            LOGGER.info("[BRAIN] chunk received"); yield token
                    except json.JSONDecodeError:
                        continue
            LOGGER.info("[LLM] Stream completed")
            LOGGER.info("[LLM] Total response length: %d", len("".join(full_response)))
        except (urllib.error.URLError, TimeoutError) as exc:
            LOGGER.error("Ollama grounded inference failed: %s", exc)
            yield offline_reply(prompt)
            return

        cleaned = self._cleanup("".join(full_response))
        self._store_assistant(cleaned)

    def _request_json(self, endpoint: str, payload: dict, timeout: int = 10) -> dict:
        """Helper to send a JSON request and return the JSON response."""
        req = urllib.request.Request(
            f"{CONFIG.ai.ollama_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _detect_model(self) -> str | None:
        try:
            req = urllib.request.Request(f"{CONFIG.ai.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", [])]
                for preferred in CONFIG.ai.preferred_models:
                    for model in models:
                        if model.startswith(preferred):
                            return model
        except Exception as exc:
            LOGGER.warning("Could not contact Ollama to detect models: %s", exc)
        return None

    def _store_assistant(self, response: str) -> None:
        self.context.add("assistant", response)
        self.memory.add_message("assistant", response)

    @staticmethod
    def _cleanup(text: str) -> str:
        return text.strip().replace("\x00", "")
