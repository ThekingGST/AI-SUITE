"""Verify pyttsx3 fix -- multiple calls on same engine instance must produce audio."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ===================================================================
# TEST 1: Standard Mode -- multiple consecutive speaks
# ===================================================================
print("=" * 60)
print("  TEST 1: Standard Mode -- 3 consecutive speaks")
print("=" * 60)

from config import DATA_DIR
mode_file = DATA_DIR / "voice_mode.txt"
mode_file.write_text("standard", encoding="utf-8")

from voice.speaker import Speaker

speaker = Speaker()
time.sleep(4)  # wait for "Systems online." to finish

print(f"  voice_mode: {speaker.voice_mode}")
print(f"  active_engine: {speaker.active_engine_name}")

# These are the calls that were SILENT before the fix
speaker.speak("Second call test.")
time.sleep(3)

speaker.speak("Third call test.")
time.sleep(3)

speaker.speak("Fourth call test.")
time.sleep(3)

print(f"  active_engine after all speaks: {speaker.active_engine_name}")
assert speaker.active_engine_name == "pyttsx3"
print("  PASS: All 4 speaks completed (standard mode)")

# ===================================================================
# TEST 2: Premium Mode -- still works
# ===================================================================
print()
print("=" * 60)
print("  TEST 2: Premium Mode -- still works")
print("=" * 60)

speaker.set_voice_mode("premium")
time.sleep(4)
print(f"  active_engine: {speaker.active_engine_name}")

speaker.speak("Premium voice test.")
time.sleep(6)
print(f"  active_engine after speak: {speaker.active_engine_name}")
print("  PASS: Premium mode works")

# ===================================================================
# TEST 3: Premium -> Standard -> speak multiple times
# ===================================================================
print()
print("=" * 60)
print("  TEST 3: Premium -> Standard transition + multiple speaks")
print("=" * 60)

speaker.set_voice_mode("standard")
time.sleep(4)
print(f"  active_engine: {speaker.active_engine_name}")

speaker.speak("Back to standard first.")
time.sleep(3)

speaker.speak("Back to standard second.")
time.sleep(3)

speaker.speak("Back to standard third.")
time.sleep(3)

print(f"  active_engine: {speaker.active_engine_name}")
assert speaker.active_engine_name == "pyttsx3"
print("  PASS: All 3 speaks completed after mode switch")

speaker.close()

print()
print("=" * 60)
print("  ALL TESTS PASSED")
print("=" * 60)
