"""Instrumented JARVIS launcher -- traces the full TTS pipeline.

Patches Speaker, TTSManager, Pyttsx3Engine, and ElevenLabsEngine at
runtime to log every decision point.  No production files are modified.

Usage:  python jarvis_tts_trace.py
"""
import inspect
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# -- Trace infrastructure -----------------------------------------------------

_TRACE_FILE = Path(__file__).resolve().parent / "data" / "tts_trace.log"
_TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
_TRACE_FILE.write_text("", encoding="utf-8")  # clear old trace


def _trace(msg: str) -> None:
    line = f"[TTS-TRACE {time.strftime('%H:%M:%S.', time.localtime())}{int(time.time()*1000)%1000:03d}] {msg}"
    print(line, flush=True)
    with open(_TRACE_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _caller_info(depth: int = 2) -> str:
    frame = sys._getframe(depth)
    fname = frame.f_code.co_filename.replace("\\", "/").rsplit("/", 1)[-1]
    return f"{fname}:{frame.f_lineno}"


# -- Patch Speaker -------------------------------------------------------------

from voice import speaker as _sp_mod

_OrigSpeaker = _sp_mod.Speaker

_orig_sp_init = _OrigSpeaker.__init__
def _traced_sp_init(self):
    mode = _sp_mod._load_voice_mode()
    _trace(f"Speaker.__init__() persisted_mode={mode}")
    _orig_sp_init(self)
    _trace(f"Speaker.__init__() done -> voice_mode={self._voice_mode}")
_OrigSpeaker.__init__ = _traced_sp_init

_orig_sp_speak = _OrigSpeaker.speak
def _traced_sp_speak(self, text):
    _trace(f"Speaker.speak('{text[:60]}') enabled={self._enabled} mode={self._voice_mode} caller={_caller_info()}")
    _orig_sp_speak(self, text)
_OrigSpeaker.speak = _traced_sp_speak

_orig_sp_set_enabled = _OrigSpeaker.set_enabled
def _traced_sp_set_enabled(self, enabled):
    _trace(f"Speaker.set_enabled({enabled}) was={self._enabled} caller={_caller_info()}")
    _orig_sp_set_enabled(self, enabled)
_OrigSpeaker.set_enabled = _traced_sp_set_enabled

_orig_sp_set_voice_mode = _OrigSpeaker.set_voice_mode
def _traced_sp_set_voice_mode(self, mode):
    _trace(f"Speaker.set_voice_mode('{mode}') was={self._voice_mode} caller={_caller_info()}")
    _orig_sp_set_voice_mode(self, mode)
_OrigSpeaker.set_voice_mode = _traced_sp_set_voice_mode

# Patch _process_queue to trace every job and every decision
_orig_sp_pq = _OrigSpeaker._process_queue
def _traced_sp_pq(self):
    _trace("Speaker._process_queue() ENTERED -- worker loop starting")
    while True:
        job = self._queue.get()
        job_desc = f"text='{job.text[:60]}'" if job.text else (f"switch_mode={job.switch_mode}" if job.switch_mode else "shutdown")
        _trace(f"Worker GOT job: {job_desc}")

        if job.shutdown:
            _trace("Worker: SHUTDOWN received")
            break
        if job.switch_mode:
            _trace(f"Worker: processing mode switch -> {job.switch_mode}")
            self._handle_mode_switch(job.switch_mode)
            continue
        if not job.text:
            _trace("Worker: SKIP (empty text)")
            continue
        if not self.enabled:
            _trace(f"Worker: DROPPED (enabled=False) text='{job.text[:60]}'")
            continue

        try:
            with self._state_lock:
                self._speaking = True
            _trace(f"Worker: SPEAK START text='{job.text[:60]}' engine={self.active_engine_name}")
            time.sleep(0.22)
            self._tts_manager.speak(job.text)
            _trace(f"Worker: SPEAK END text='{job.text[:60]}' engine={self.active_engine_name}")
        except Exception as exc:
            _trace(f"Worker: EXCEPTION during speak: {exc}")
        finally:
            with self._state_lock:
                self._speaking = False
                self._last_spoken_at = time.time()
_OrigSpeaker._process_queue = _traced_sp_pq


# -- Patch TTSManager ---------------------------------------------------------

from voice.tts import tts_manager as _mgr_mod

_OrigMgr = _mgr_mod.TTSManager

_orig_mgr_speak = _OrigMgr.speak
def _traced_mgr_speak(self, text):
    p = self._primary
    f = self._fallback
    _trace(
        f"TTSManager.speak('{text[:60]}') "
        f"primary={p.engine_name() if p else 'None'}(avail={p.is_available() if p else 'N/A'}) "
        f"fallback={f.engine_name() if f else 'None'}"
    )
    _orig_mgr_speak(self, text)
    _trace(f"TTSManager.speak() RETURNED active={self._active_name}")
_OrigMgr.speak = _traced_mgr_speak

_orig_mgr_init = _OrigMgr.initialize
def _traced_mgr_init(self):
    _trace(f"TTSManager.initialize() requested_engine={self._requested_engine} api_key_set={bool(self._api_key)}")
    _orig_mgr_init(self)
    _trace(f"TTSManager.initialize() DONE primary={self._primary.engine_name() if self._primary else 'None'} active={self._active_name}")
_OrigMgr.initialize = _traced_mgr_init


# -- Patch Pyttsx3Engine -------------------------------------------------------

from voice.tts import pyttsx3_engine as _p3_mod

_OrigP3 = _p3_mod.Pyttsx3Engine

_orig_p3_speak = _OrigP3.speak
def _traced_p3_speak(self, text):
    _trace(f"Pyttsx3Engine.speak('{text[:60]}') engine_exists={self._engine is not None} avail={self._available}")
    t0 = time.monotonic()
    _orig_p3_speak(self, text)
    elapsed = time.monotonic() - t0
    _trace(f"Pyttsx3Engine.speak() DONE elapsed={elapsed:.3f}s {'SUSPECT_SILENT' if elapsed < 0.3 else 'OK'}")
_OrigP3.speak = _traced_p3_speak

_orig_p3_init = _OrigP3.initialize
def _traced_p3_init(self):
    _trace("Pyttsx3Engine.initialize() START")
    _orig_p3_init(self)
    _trace(f"Pyttsx3Engine.initialize() DONE avail={self._available} engine={self._engine is not None}")
_OrigP3.initialize = _traced_p3_init

_orig_p3_close = _OrigP3.close
def _traced_p3_close(self):
    _trace(f"Pyttsx3Engine.close() engine={self._engine is not None} com={self._com_initialized}")
    _orig_p3_close(self)
    _trace("Pyttsx3Engine.close() DONE")
_OrigP3.close = _traced_p3_close


# -- Patch ElevenLabsEngine ----------------------------------------------------

from voice.tts import elevenlabs_engine as _el_mod

_OrigEL = _el_mod.ElevenLabsEngine

_orig_el_speak = _OrigEL.speak
def _traced_el_speak(self, text):
    _trace(f"ElevenLabsEngine.speak('{text[:60]}') avail={self._available}")
    _orig_el_speak(self, text)
    _trace("ElevenLabsEngine.speak() DONE")
_OrigEL.speak = _traced_el_speak


# -- Launch JARVIS -------------------------------------------------------------

_trace("=" * 60)
_trace("JARVIS LAUNCHING WITH TTS TRACE")
_trace(f"voice_mode file: {_sp_mod._VOICE_MODE_FILE}")
_trace(f"voice_mode value: {_sp_mod._load_voice_mode()}")
_trace("=" * 60)

from main import main
raise SystemExit(main())
