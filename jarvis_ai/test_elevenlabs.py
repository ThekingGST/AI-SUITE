"""ElevenLabs TTS integration diagnostic script for JARVIS.

Run from the project root:
    python jarvis_ai/test_elevenlabs.py

Tests each stage of the pipeline and reports pass/fail with details.
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

# Ensure jarvis_ai is on sys.path.
_JARVIS_DIR = Path(__file__).resolve().parent
if str(_JARVIS_DIR) not in sys.path:
    sys.path.insert(0, str(_JARVIS_DIR))

PASS = "PASS"
FAIL = "FAIL"
results: list[tuple[str, bool, str]] = []


def step(name: str):
    """Decorator that records pass/fail for a diagnostic step."""
    def decorator(fn):
        def wrapper():
            try:
                detail = fn()
                results.append((name, True, detail or "OK"))
                print(f"  {PASS} {name}: {detail or 'OK'}")
                return True
            except Exception as exc:
                results.append((name, False, str(exc)))
                print(f"  {FAIL} {name}: {exc}")
                return False
        return wrapper
    return decorator


# ── STEP 1: .env file ──────────────────────────────────────────────────────

@step("1. .env file exists")
def check_env_file():
    env_path = _JARVIS_DIR / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f"No .env at {env_path}")
    size = env_path.stat().st_size
    if size == 0:
        raise ValueError(f".env exists but is EMPTY (0 bytes) at {env_path}")
    return f"{size} bytes at {env_path}"


# ── STEP 2: python-dotenv ──────────────────────────────────────────────────

@step("2. python-dotenv installed")
def check_dotenv():
    from dotenv import load_dotenv  # noqa: F401
    return "import successful"


# ── STEP 3: load_dotenv ────────────────────────────────────────────────────

@step("3. load_dotenv() loads .env")
def load_env():
    from dotenv import load_dotenv
    env_path = _JARVIS_DIR / ".env"
    loaded = load_dotenv(env_path, override=True)
    if not loaded:
        raise RuntimeError(f"load_dotenv returned False for {env_path}")
    return "loaded successfully"


# ── STEP 4: env vars ──────────────────────────────────────────────────────

@step("4. ELEVENLABS_API_KEY set")
def check_api_key():
    key = os.getenv("ELEVENLABS_API_KEY", "")
    if not key:
        raise ValueError("ELEVENLABS_API_KEY is empty or not set")
    return f"length={len(key)}, starts_with={key[:8]}..."


@step("5. ELEVENLABS_VOICE_ID set")
def check_voice_id():
    vid = os.getenv("ELEVENLABS_VOICE_ID", "")
    if not vid:
        raise ValueError("ELEVENLABS_VOICE_ID is empty or not set")
    return vid


@step("6. TTS_ENGINE value")
def check_tts_engine():
    engine = os.getenv("TTS_ENGINE", "")
    if not engine:
        raise ValueError("TTS_ENGINE is empty or not set")
    return engine


# ── STEP 7: config.py ─────────────────────────────────────────────────────

@step("7. CONFIG loads correctly")
def check_config():
    from config import CONFIG
    if not CONFIG.voice.elevenlabs_api_key:
        raise ValueError("CONFIG.voice.elevenlabs_api_key is empty")
    return (
        f"tts_engine={CONFIG.voice.tts_engine}, "
        f"api_key_len={len(CONFIG.voice.elevenlabs_api_key)}, "
        f"voice_id={CONFIG.voice.elevenlabs_voice_id}"
    )


# ── STEP 8: elevenlabs SDK ────────────────────────────────────────────────

@step("8. elevenlabs package importable")
def check_elevenlabs_import():
    from elevenlabs import ElevenLabs  # noqa: F401
    import elevenlabs
    return f"version={getattr(elevenlabs, '__version__', 'unknown')}"


# ── STEP 9: ElevenLabs client ─────────────────────────────────────────────

@step("9. ElevenLabs client creation")
def check_client_creation():
    from elevenlabs import ElevenLabs
    key = os.getenv("ELEVENLABS_API_KEY", "")
    client = ElevenLabs(api_key=key)
    return f"client created: {type(client).__name__}"


# ── STEP 10: connectivity ─────────────────────────────────────────────────

@step("10. ElevenLabs API connectivity")
def check_connectivity():
    from elevenlabs import ElevenLabs
    key = os.getenv("ELEVENLABS_API_KEY", "")
    client = ElevenLabs(api_key=key)
    voices = client.voices.get_all()
    count = len(voices.voices) if hasattr(voices, "voices") else 0
    return f"{count} voices available"


# ── STEP 11: pygame ───────────────────────────────────────────────────────

@step("11. pygame importable")
def check_pygame():
    import pygame
    return f"version={pygame.version.ver}"


@step("12. pygame.mixer init")
def check_mixer():
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    info = pygame.mixer.get_init()
    return f"freq={info[0]}, size={info[1]}, channels={info[2]}"


# ── STEP 13: speech generation ─────────────────────────────────────────────

@step("13. ElevenLabs speech generation")
def check_speech_generation():
    from elevenlabs import ElevenLabs
    key = os.getenv("ELEVENLABS_API_KEY", "")
    vid = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    client = ElevenLabs(api_key=key)
    start = time.monotonic()
    response = client.text_to_speech.convert(
        voice_id=vid,
        text="Systems online.",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    audio_bytes = b"".join(chunk for chunk in response)
    elapsed = time.monotonic() - start
    if not audio_bytes:
        raise RuntimeError("API returned empty audio")
    # Save for inspection.
    tmp_path = _JARVIS_DIR / "data" / "test_elevenlabs_output.mp3"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(audio_bytes)
    return f"{len(audio_bytes)} bytes in {elapsed:.2f}s, saved to {tmp_path}"


# ── STEP 14: audio playback ───────────────────────────────────────────────

@step("14. pygame audio playback")
def check_playback():
    import pygame
    tmp_path = _JARVIS_DIR / "data" / "test_elevenlabs_output.mp3"
    if not tmp_path.exists():
        raise FileNotFoundError("No test audio file — step 13 must pass first")
    audio_bytes = tmp_path.read_bytes()
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    sound = pygame.mixer.Sound(io.BytesIO(audio_bytes))
    channel = sound.play()
    if not channel:
        raise RuntimeError("pygame.mixer.Sound.play() returned no channel")
    start = time.monotonic()
    while channel.get_busy():
        pygame.time.wait(50)
    elapsed = time.monotonic() - start
    return f"played {len(audio_bytes)} bytes in {elapsed:.2f}s"


# ── STEP 15: full ElevenLabsEngine ─────────────────────────────────────────

@step("15. ElevenLabsEngine full integration")
def check_engine_integration():
    from voice.tts.elevenlabs_engine import ElevenLabsEngine
    key = os.getenv("ELEVENLABS_API_KEY", "")
    vid = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    engine = ElevenLabsEngine(key, vid)
    engine.initialize()
    if not engine.is_available():
        raise RuntimeError("engine.is_available() returned False after init")
    engine.speak("Jarvis online. ElevenLabs integration verified.")
    name = engine.engine_name()
    engine.close()
    return f"engine_name={name}, spoke successfully"


# ── STEP 16: TTSManager ───────────────────────────────────────────────────

@step("16. TTSManager selects ElevenLabs")
def check_tts_manager():
    from voice.tts.tts_manager import TTSManager
    key = os.getenv("ELEVENLABS_API_KEY", "")
    vid = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    mgr = TTSManager("elevenlabs", key, vid)
    mgr.initialize()
    active = mgr.active_engine_name
    if active != "elevenlabs":
        mgr.close()
        raise RuntimeError(f"Expected 'elevenlabs', got '{active}'")
    mgr.close()
    return f"active_engine={active}"


# ── MAIN ───────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 60)
    print("  JARVIS — ElevenLabs TTS Diagnostic")
    print("=" * 60)
    print()

    all_steps = [
        check_env_file,
        check_dotenv,
        load_env,
        check_api_key,
        check_voice_id,
        check_tts_engine,
        check_config,
        check_elevenlabs_import,
        check_client_creation,
        check_connectivity,
        check_pygame,
        check_mixer,
        check_speech_generation,
        check_playback,
        check_engine_integration,
        check_tts_manager,
    ]

    for step_fn in all_steps:
        step_fn()

    print()
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"  RESULTS: {passed} passed, {failed} failed out of {len(results)}")
    print("=" * 60)

    if failed:
        print()
        print("FAILURES:")
        for name, ok, detail in results:
            if not ok:
                print(f"  {FAIL} {name}")
                print(f"    {detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
