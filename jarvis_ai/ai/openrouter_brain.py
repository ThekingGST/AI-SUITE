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
from shared.config.secrets_manager import SecretsManager


class OpenRouterBrain:
    """Cloud LLM brain using direct HTTP requests to OpenRouter API."""

    def __init__(self, memory: MemoryStore, retriever: Retriever = None) -> None:
        self.retriever = retriever
        self.memory = memory
        self.context = ContextManager(CONFIG.ai.max_history_messages)
        self.context.load(memory.recent_messages(CONFIG.ai.max_history_messages))
        self.model = "meta-llama/llama-3-8b-instruct:free" # Default fast openrouter model
        LOGGER.info("OpenRouterBrain initialized.")

    def refresh_model(self) -> str | None:
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
        LOGGER.info("[BRAIN] ask_stream (OpenRouter) started")
        LOGGER.info("[LLM] Language: %s", language or "English")
        
        api_key = SecretsManager().get_secret("OPENROUTER_API_KEY")
        if not api_key:
            reply = "Cloud AI requires an OpenRouter API key. Add your key in Settings -> AI Providers."
            self._store_assistant(reply)
            yield reply
            return

        self.memory.add_message("user", prompt)
        self.context.add("user", prompt)
        
        system_content = build_system_prompt()
        if language and language.lower() not in ("english", "en"):
            system_content += f"\n\nIMPORTANT: You MUST respond to the user in {language}. Do NOT respond in English."
        
        # Inject relevant active long-term memories
        t0 = time.perf_counter()
        relevant_memories = self.memory.search_memories(prompt, limit=5)
        t_mem = (time.perf_counter() - t0) * 1000
        LOGGER.info("[TIMING] Memory search: %.2f ms", t_mem)
        
        if relevant_memories:
            mem_text = "\n".join(f"- {m}" for m in relevant_memories)
            mem_block = f"\n\n<LONG_TERM_MEMORY>\n{mem_text}\n</LONG_TERM_MEMORY>"
            system_content += mem_block
            LOGGER.info("[BRAIN] Injected %d memories: %s", len(relevant_memories), mem_block.strip())
            
        t0 = time.perf_counter()
        if self.retriever:
            doc_context = self.retriever.retrieve(prompt)
            if doc_context:
                system_content += "\n\n" + doc_context
        t_doc = (time.perf_counter() - t0) * 1000
        LOGGER.info("[TIMING] Document search: %.2f ms", t_doc)
                
        messages = [{"role": "system", "content": system_content}, *self.context.messages()]
        LOGGER.info("[LLM] Cloud prompt prepared")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        full_response = []
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://github.com/v1",
                    "X-Title": "AI Suite"
                },
                method="POST",
            )
            t0 = time.perf_counter()
            LOGGER.info("[LLM] Cloud connection established")
            with urllib.request.urlopen(req, timeout=CONFIG.ai.response_timeout_seconds) as response:
                t_conn = (time.perf_counter() - t0) * 1000
                LOGGER.info("[TIMING] LLM connection: %.2f ms", t_conn)
                
                first_token = True
                for line in response:
                    if not line:
                        continue
                    line_str = line.decode("utf-8").strip()
                    if line_str == "data: [DONE]":
                        break
                    if line_str.startswith("data: "):
                        json_str = line_str[6:]
                        try:
                            data = json.loads(json_str)
                            choices = data.get("choices", [])
                            if choices:
                                token = choices[0].get("delta", {}).get("content", "")
                                if token:
                                    if first_token:
                                        t_ttft = (time.perf_counter() - t0) * 1000
                                        LOGGER.info("[LLM] First token received")
                                        LOGGER.info("[TIMING] Time to first token: %.2f ms", t_ttft)
                                        first_token = False
                                    full_response.append(token)
                                    yield token
                        except json.JSONDecodeError:
                            continue
            t_gen = (time.perf_counter() - t0) * 1000
            LOGGER.info("[LLM] Stream completed")
            LOGGER.info("[TIMING] Total LLM generation: %.2f ms", t_gen)
            LOGGER.info("[LLM] Total response length: %d", len("".join(full_response)))
        except (urllib.error.URLError, TimeoutError) as exc:
            LOGGER.error("OpenRouter inference failed: %s", exc)
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
        LOGGER.info("[LLM] Cloud grounded request started")
        LOGGER.info("[LLM] Language: %s", language or "English")
        api_key = SecretsManager().get_secret("OPENROUTER_API_KEY")
        if not api_key:
            reply = "Cloud AI requires an OpenRouter API key. Add your key in Settings -> AI Providers."
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

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        full_response = []
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://github.com/v1",
                    "X-Title": "AI Suite"
                },
                method="POST",
            )
            LOGGER.info("[LLM] Cloud grounded connection established")
            with urllib.request.urlopen(req, timeout=CONFIG.ai.response_timeout_seconds) as response:
                first_token = True
                for line in response:
                    if not line:
                        continue
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        line_str = line_str[6:]
                    if line_str == "[DONE]":
                        break
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        choices = data.get("choices", [])
                        if choices:
                            token = choices[0].get("delta", {}).get("content", "")
                            if token:
                                if first_token:
                                    LOGGER.info("[LLM] First token received")
                                    first_token = False
                                full_response.append(token)
                                yield token
                    except json.JSONDecodeError:
                        continue
            LOGGER.info("[LLM] Stream completed")
            LOGGER.info("[LLM] Total response length: %d", len("".join(full_response)))
        except (urllib.error.URLError, TimeoutError) as exc:
            LOGGER.error("OpenRouter grounded inference failed: %s", exc)
            yield offline_reply(prompt)
            return

        cleaned = self._cleanup("".join(full_response))
        self._store_assistant(cleaned)

    def _store_assistant(self, response: str) -> None:
        self.context.add("assistant", response)
        self.memory.add_message("assistant", response)

    @staticmethod
    def _cleanup(text: str) -> str:
        return text.strip().replace("\x00", "")

