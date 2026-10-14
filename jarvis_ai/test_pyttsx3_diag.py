"""Focused pyttsx3 diagnostic -- isolate why speech is silent."""
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ===================================================================
# TEST 1: pyttsx3 standalone (simplest possible)
# ===================================================================
print("=" * 60)
print("  TEST 1: pyttsx3 standalone (main thread, no COM)")
print("=" * 60)

import pyttsx3
print(f"  pyttsx3 version: {pyttsx3.__version__ if hasattr(pyttsx3, '__version__') else 'unknown'}")

engine = pyttsx3.init()
voices = engine.getProperty("voices") or []
rate = engine.getProperty("rate")
volume = engine.getProperty("volume")
print(f"  Voices found: {len(voices)}")
for v in voices:
    print(f"    - {v.id}")
    print(f"      name: {v.name}")
print(f"  Rate: {rate}")
print(f"  Volume: {volume}")

print("  Calling engine.say('Test one standalone')...")
engine.say("Test one standalone")
print("  Calling engine.runAndWait()...")
t0 = time.monotonic()
engine.runAndWait()
elapsed = time.monotonic() - t0
print(f"  runAndWait() returned in {elapsed:.3f}s")
if elapsed < 0.3:
    print("  WARNING: runAndWait() returned suspiciously fast -- likely no audio played")
else:
    print("  OK: Took enough time to have played audio")
engine.stop()
del engine

# ===================================================================
# TEST 2: pyttsx3 with explicit COM (matching our Pyttsx3Engine)
# ===================================================================
print()
print("=" * 60)
print("  TEST 2: pyttsx3 with pythoncom.CoInitialize() (main thread)")
print("=" * 60)

try:
    import pythoncom
    pythoncom.CoInitialize()
    print("  COM: CoInitialize() succeeded (STA)")
except Exception as exc:
    print(f"  COM: CoInitialize() failed: {exc}")

engine2 = pyttsx3.init()
engine2.setProperty("rate", 165)
engine2.setProperty("volume", 1.0)
print("  Calling engine.say('Test two with COM')...")
engine2.say("Test two with COM")
print("  Calling engine.runAndWait()...")
t0 = time.monotonic()
engine2.runAndWait()
elapsed = time.monotonic() - t0
print(f"  runAndWait() returned in {elapsed:.3f}s")
if elapsed < 0.3:
    print("  WARNING: runAndWait() returned suspiciously fast")
else:
    print("  OK: Took enough time to have played audio")
engine2.stop()
del engine2

try:
    pythoncom.CoUninitialize()
except Exception:
    pass

# ===================================================================
# TEST 3: pyttsx3 on worker thread (matching Speaker architecture)
# ===================================================================
print()
print("=" * 60)
print("  TEST 3: pyttsx3 on worker thread with COM")
print("=" * 60)

result = {}

def worker():
    try:
        import pythoncom as pc
        pc.CoInitialize()
        result["com"] = "STA initialized"
    except Exception as exc:
        result["com"] = f"failed: {exc}"

    e = pyttsx3.init()
    e.setProperty("rate", 165)
    e.setProperty("volume", 1.0)
    result["engine"] = "created"

    e.say("Test three on worker thread")
    t0 = time.monotonic()
    e.runAndWait()
    elapsed = time.monotonic() - t0
    result["elapsed"] = elapsed
    result["fast"] = elapsed < 0.3

    e.stop()
    try:
        pc.CoUninitialize()
    except Exception:
        pass
    result["done"] = True

t = threading.Thread(target=worker, daemon=True)
t.start()
t.join(timeout=15)

print(f"  COM: {result.get('com', 'not run')}")
print(f"  Engine: {result.get('engine', 'not created')}")
elapsed = result.get('elapsed', 0)
print(f"  runAndWait() returned in {elapsed:.3f}s")
if result.get("fast"):
    print("  WARNING: runAndWait() returned suspiciously fast")
else:
    print("  OK: Took enough time to have played audio")
print(f"  Completed: {result.get('done', False)}")

# ===================================================================
# TEST 4: Full Pyttsx3Engine path
# ===================================================================
print()
print("=" * 60)
print("  TEST 4: Full Pyttsx3Engine on worker thread")
print("=" * 60)

result4 = {}

def worker4():
    from voice.tts.pyttsx3_engine import Pyttsx3Engine
    eng = Pyttsx3Engine()
    eng.initialize()
    result4["available"] = eng.is_available()
    result4["engine_name"] = eng.engine_name()

    t0 = time.monotonic()
    eng.speak("Test four full engine path")
    elapsed = time.monotonic() - t0
    result4["elapsed"] = elapsed
    result4["fast"] = elapsed < 0.3
    eng.close()
    result4["done"] = True

t4 = threading.Thread(target=worker4, daemon=True)
t4.start()
t4.join(timeout=15)

print(f"  Available: {result4.get('available')}")
print(f"  Engine name: {result4.get('engine_name')}")
elapsed4 = result4.get('elapsed', 0)
print(f"  speak() returned in {elapsed4:.3f}s")
if result4.get("fast"):
    print("  WARNING: speak() returned suspiciously fast")
else:
    print("  OK: Took enough time to have played audio")
print(f"  Completed: {result4.get('done', False)}")

# ===================================================================
# TEST 5: Direct Windows SAPI via comtypes (bypass pyttsx3 entirely)
# ===================================================================
print()
print("=" * 60)
print("  TEST 5: Direct SAPI5 via comtypes")
print("=" * 60)

try:
    import comtypes.client
    sapi = comtypes.client.CreateObject("SAPI.SpVoice")
    sapi.Rate = 2
    sapi.Volume = 100
    print("  SAPI.SpVoice created directly")
    print("  Speaking 'Test five direct SAPI'...")
    t0 = time.monotonic()
    sapi.Speak("Test five direct SAPI")
    elapsed = time.monotonic() - t0
    print(f"  Speak() returned in {elapsed:.3f}s")
    if elapsed < 0.3:
        print("  WARNING: Speak() returned suspiciously fast -- SAPI itself may be broken")
    else:
        print("  OK: SAPI produced audio")
    del sapi
except Exception as exc:
    print(f"  SAPI test failed: {exc}")

# ===================================================================
# SUMMARY
# ===================================================================
print()
print("=" * 60)
print("  DIAGNOSIS SUMMARY")
print("=" * 60)
