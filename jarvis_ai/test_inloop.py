"""Test the correct pyttsx3 workaround -- del + _inLoop reset + fresh init."""
import sys
sys.path.insert(0, "d:/Coding/Jarvis/jarvis_ai")

import pyttsx3
import time


def speak(text):
    e = pyttsx3.init()
    e.setProperty("rate", 165)
    e.say(text)
    t = time.monotonic()
    e.runAndWait()
    elapsed = time.monotonic() - t
    print(f"  {text}: {elapsed:.3f}s {'OK' if elapsed > 0.3 else 'SILENT'}")
    e.stop()
    del e
    # Reset the class-level _inLoop flag that pyttsx3 leaves stuck
    pyttsx3.engine.Engine._inLoop = False


print("Test: del + _inLoop reset + fresh init per call")
speak("Call one")
speak("Call two")
speak("Call three")
speak("Call four")
print("Done.")
