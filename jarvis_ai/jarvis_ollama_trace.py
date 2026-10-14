"""Instrumented JARVIS launcher -- traces the Ollama AI generation path.

Patches OllamaBrain, CommandRouter, and _command_loop to trace
every decision point from user input to Ollama response.

Usage:  python jarvis_ollama_trace.py
Then type: "Tell me about SNIST" in the command box.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# -- Trace infrastructure -----------------------------------------------------

_TRACE_FILE = Path(__file__).resolve().parent / "data" / "ollama_trace.log"
_TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
_TRACE_FILE.write_text("", encoding="utf-8")


def _trace(msg: str) -> None:
    line = f"[OLLAMA-TRACE {time.strftime('%H:%M:%S.', time.localtime())}{int(time.time()*1000)%1000:03d}] {msg}"
    print(line, flush=True)
    with open(_TRACE_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# -- Patch OllamaBrain ---------------------------------------------------------

from ai import ollama_brain as _brain_mod

_OrigBrain = _brain_mod.OllamaBrain

_orig_init = _OrigBrain.__init__
def _traced_init(self, memory):
    _trace("OllamaBrain.__init__() START")
    _orig_init(self, memory)
    _trace(f"OllamaBrain.__init__() DONE model={self.model!r}")
_OrigBrain.__init__ = _traced_init

_orig_select = _OrigBrain._select_model
def _traced_select(self):
    _trace("OllamaBrain._select_model() START")
    try:
        result = _orig_select(self)
        _trace(f"OllamaBrain._select_model() DONE result={result!r}")
        return result
    except Exception as exc:
        _trace(f"OllamaBrain._select_model() EXCEPTION: {exc}")
        raise
_OrigBrain._select_model = _traced_select

_orig_ask = _OrigBrain.ask
def _traced_ask(self, prompt, on_token=None):
    _trace(f"OllamaBrain.ask('{prompt[:80]}') model={self.model!r}")
    if not self.model:
        _trace("OllamaBrain.ask() -> OFFLINE FALLBACK (model is None)")
    result = _orig_ask(self, prompt, on_token)
    _trace(f"OllamaBrain.ask() RETURNED ({len(result)} chars): '{result[:100]}'")
    return result
_OrigBrain.ask = _traced_ask

_orig_refresh = _OrigBrain.refresh_model
def _traced_refresh(self):
    _trace("OllamaBrain.refresh_model() called")
    result = _orig_refresh(self)
    _trace(f"OllamaBrain.refresh_model() DONE model={result!r}")
    return result
_OrigBrain.refresh_model = _traced_refresh

_orig_stream = _OrigBrain._stream_chat
def _traced_stream(self, prompt, on_token):
    _trace(f"OllamaBrain._stream_chat() START model={self.model} prompt='{prompt[:80]}'")
    try:
        for token in _orig_stream(self, prompt, on_token):
            yield token
        _trace("OllamaBrain._stream_chat() DONE (all tokens received)")
    except Exception as exc:
        _trace(f"OllamaBrain._stream_chat() EXCEPTION: {type(exc).__name__}: {exc}")
        raise
_OrigBrain._stream_chat = _traced_stream


# -- Patch CommandRouter -------------------------------------------------------

from voice import command_router as _router_mod

_OrigRouter = _router_mod.CommandRouter

_orig_handle = _OrigRouter.handle
def _traced_handle(self, raw_text, speak=True):
    _trace(f"CommandRouter.handle('{raw_text[:80]}') speak={speak}")
    result = _orig_handle(self, raw_text, speak)
    _trace(f"CommandRouter.handle() RETURNED ({len(result)} chars): '{result[:100]}'")
    return result
_OrigRouter.handle = _traced_handle

_orig_route = _OrigRouter._route
def _traced_route(self, text):
    _trace(f"CommandRouter._route('{text[:80]}')")
    result = _orig_route(self, text)
    _trace(f"CommandRouter._route() RETURNED: '{result[:100]}'")
    return result
_OrigRouter._route = _traced_route


# -- Launch JARVIS -------------------------------------------------------------

_trace("=" * 60)
_trace("JARVIS LAUNCHING WITH OLLAMA TRACE")
_trace("=" * 60)

from main import main
raise SystemExit(main())
