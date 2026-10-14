"""Quick test of ElevenLabs voice access on free tier."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

import os
from elevenlabs import ElevenLabs

api_key = os.getenv("ELEVENLABS_API_KEY", "")
client = ElevenLabs(api_key=api_key)

# Test 1: Try Rachel (library voice) with multilingual v2
print("=== Test 1: Rachel + eleven_multilingual_v2 ===")
try:
    resp = client.text_to_speech.convert(
        voice_id="21m00Tcm4TlvDq8ikWAM",
        text="test",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    audio = b"".join(resp)
    print(f"  SUCCESS: {len(audio)} bytes")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}")
    body = getattr(e, "body", None)
    if body:
        detail = body.get("detail", {}) if isinstance(body, dict) else body
        print(f"  Detail: {detail}")

# Test 2: Try Rachel with monolingual v1 (older, possibly less restricted)
print("\n=== Test 2: Rachel + eleven_monolingual_v1 ===")
try:
    resp = client.text_to_speech.convert(
        voice_id="21m00Tcm4TlvDq8ikWAM",
        text="test",
        model_id="eleven_monolingual_v1",
        output_format="mp3_44100_128",
    )
    audio = b"".join(resp)
    print(f"  SUCCESS: {len(audio)} bytes")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}")
    body = getattr(e, "body", None)
    if body:
        detail = body.get("detail", {}) if isinstance(body, dict) else body
        print(f"  Detail: {detail}")

# Test 3: Try to list available voices
print("\n=== Test 3: List voices (checking permissions) ===")
try:
    voices = client.voices.get_all()
    count = len(voices.voices) if hasattr(voices, "voices") else 0
    print(f"  SUCCESS: {count} voices")
    if hasattr(voices, "voices"):
        for v in voices.voices[:5]:
            print(f"    - {v.voice_id}: {v.name}")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}")
    body = getattr(e, "body", None)
    if body:
        detail = body.get("detail", {}) if isinstance(body, dict) else body
        print(f"  Detail: {detail}")

# Test 4: Try generating a voice clone / using a created voice
# Free tier allows created voices. Let's see if any exist.
print("\n=== Test 4: Account info ===")
try:
    # Try a simple generation with the default model
    resp = client.text_to_speech.convert(
        voice_id="21m00Tcm4TlvDq8ikWAM",
        text="test",
        model_id="eleven_turbo_v2",
        output_format="mp3_44100_128",
    )
    audio = b"".join(resp)
    print(f"  SUCCESS with turbo_v2: {len(audio)} bytes")
except Exception as e:
    print(f"  FAILED with turbo_v2: {type(e).__name__}")
    body = getattr(e, "body", None)
    if body:
        detail = body.get("detail", {}) if isinstance(body, dict) else body
        print(f"  Detail: {detail}")

print("\n=== CONCLUSION ===")
print("If ALL tests failed with 'paid_plan_required', the ElevenLabs")
print("free tier does not allow API access to library voices like Rachel.")
print("Solution: Either upgrade to a paid plan, or use a cloned/custom voice.")
