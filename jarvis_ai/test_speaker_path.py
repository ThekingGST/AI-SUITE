"""Test the actual Speaker path used by JARVIS -- does audio come out?"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DATA_DIR

# Ensure standard mode for this test.
mode_file = DATA_DIR / "voice_mode.txt"
mode_file.parent.mkdir(parents=True, exist_ok=True)
mode_file.write_text("standard", encoding="utf-8")

print("=" * 60)
print("  TEST A: Speaker in Standard mode (full JARVIS path)")
print("=" * 60)

from voice.speaker import Speaker

speaker = Speaker()
# Wait for init ("Systems online." is queued in __init__)
time.sleep(5)

print(f"  voice_mode: {speaker.voice_mode}")
print(f"  active_engine: {speaker.active_engine_name}")
print(f"  is_speaking: {speaker.is_speaking}")

# Speak another phrase
print("  Queueing 'Standard mode speech test'...")
speaker.speak("Standard mode speech test.")
time.sleep(5)
print(f"  active_engine after speak: {speaker.active_engine_name}")

# ===================================================================
print()
print("=" * 60)
print("  TEST B: Switch to Premium mode at runtime")
print("=" * 60)

speaker.set_voice_mode("premium")
time.sleep(3)
print(f"  voice_mode: {speaker.voice_mode}")
print(f"  active_engine: {speaker.active_engine_name}")

speaker.speak("Premium mode speech test.")
time.sleep(8)
print(f"  active_engine after speak: {speaker.active_engine_name}")

# ===================================================================
print()
print("=" * 60)
print("  TEST C: Switch back to Standard mode")
print("=" * 60)

speaker.set_voice_mode("standard")
time.sleep(3)
print(f"  voice_mode: {speaker.voice_mode}")
print(f"  active_engine: {speaker.active_engine_name}")

speaker.speak("Back to standard mode.")
time.sleep(5)
print(f"  active_engine after speak: {speaker.active_engine_name}")

speaker.close()
print()
print("=" * 60)
print("  ALL SPEAKER TESTS COMPLETE")
print("=" * 60)
