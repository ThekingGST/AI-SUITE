import os
import sys
import time
import logging
import threading

# Add Jarvis root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jarvis_ai.utils.logger import LOGGER
from jarvis_ai.voice.speaker import Speaker
from jarvis_ai.voice.v2.events import VoiceEvent
from jarvis_ai.voice.v2.profile import DEFAULT_PROFILES

def run_hardware_test():
    # Enable info logging
    logging.getLogger().setLevel(logging.INFO)
    
    # Initialize the complete production Speaker (V2) stack
    speaker = Speaker()
    event_bus = speaker.event_bus
    manager = speaker.manager
    
    # We will track events
    finished_event = threading.Event()
    
    def on_speech_finished(payload):
        LOGGER.info("[TEST] Received SPEECH_FINISHED: %s", payload)
        finished_event.set()
        
    def on_speech_started(payload):
        LOGGER.info("[TEST] Received SPEECH_STARTED: %s", payload)

    def on_backend_changed(payload):
        LOGGER.info("[TEST] Received BACKEND_CHANGED: %s", payload)

    event_bus.subscribe(VoiceEvent.SPEECH_FINISHED, on_speech_finished)
    event_bus.subscribe(VoiceEvent.SPEECH_STARTED, on_speech_started)
    event_bus.subscribe(VoiceEvent.BACKEND_CHANGED, on_backend_changed)
    
    # Clear out the "Systems online." startup message
    finished_event.wait(timeout=5.0)
    
    try:
        test_cases = [
            ("ENGLISH", "en", "Hello! I am Jarvis. I am ready."),
            ("HINDI", "hi", "नमस्ते! मैं जार्विस हूँ। मैं हिंदी में आपसे बात कर सकता हूँ।"),
            ("TELUGU", "te", "నమస్కారం! నేను జార్విస్ను. నేను తెలుగులో మీతో మాట్లాడగలను."),
            ("ENGLISH_AGAIN", "en", "Testing consecutive playback completion.")
        ]
        
        for name, lang, text in test_cases:
            LOGGER.info(f"\n{'='*40}\n[TEST] Starting {name} ({lang})\n{'='*40}")
            
            finished_event.clear()
            
            # TTSRouter relies on text detection, but we can also forcefully set the profile just in case?
            # Actually, TTSRouter dynamically selects it. We just call speak().
            speaker.speak(text)
            
            # Wait for playback to complete (timeout 20s to account for synthesis time)
            success = finished_event.wait(timeout=20.0)
            
            if success:
                LOGGER.info(f"[TEST] {name} Playback completed successfully!")
            else:
                LOGGER.error(f"[TEST] {name} Playback TIMED OUT or FAILED!")
                
            time.sleep(1.0) # Pause between utterances
            
    finally:
        LOGGER.info("\n[TEST] Shutting down Speaker...")
        speaker.close()
        LOGGER.info("[TEST] Done.")

if __name__ == '__main__':
    run_hardware_test()
