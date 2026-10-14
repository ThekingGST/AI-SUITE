# Implementation Plan: Master Directive Stabilization

This plan configures the Voice System exactly according to the strict Master Directive to guarantee a deterministic runtime environment for the endurance test.

## User Review Required
We are temporarily disabling Pyttsx3 and ElevenLabs entirely, leaving Edge-TTS as the absolute single source of truth. If it fails, the app fails (no silent fallbacks).

## Proposed Changes

### [MODIFY] `jarvis_ai/voice/v2/profile.py`
- Modify `JarvisProfile`, `NaturalProfile`, and others to use `fallback_chain=["edge-tts"]` with NO other backends.
- Hardcode `backend_voice_overrides={"edge-tts": "en-US-GuyNeural"}`.

### [MODIFY] `jarvis_ai/voice/speaker.py`
- In `_setup_v2()`, ONLY instantiate and register `EdgeTtsBackend`.
- Remove imports and registration for `ElevenLabsBackend` and `Pyttsx3Backend`.

### [MODIFY] `jarvis_ai/ui/main_window.py`
- Update `_run_startup_diagnostics` to print the exact `STARTUP VALIDATION` checklist required by the master directive.
- Inject a `ThreadMonitor` daemon that runs every 3 seconds. It will maintain references to:
  - `SpeechManagerWorker` (from `self.speaker.manager._thread`)
  - `AudioCaptureWorker` (from `self.listener._framework._capture_worker._thread`)
  - `AudioPipelineWorker` (from `self.listener._framework._pipeline._thread`)
  - `EdgeTtsAsyncWorker` (from `self.speaker.manager._registry.get_backend("edge-tts")._thread`)
  - `JarvisCommandLoop` (from `self._command_thread`)
- If any thread dies, it will log a `FATAL` error with thread IDs and stop the application logic.

## Verification Plan
1. The user will run `python ai_suite/main.py`.
2. The UI will instantly print the `STARTUP VALIDATION` checkboxes.
3. The user will conduct the exact "Hey Jarvis" 100-repetition Endurance Test using the real microphone.
4. If ANY link in the pipeline fails, the Live Diagnostics logs will instantly expose the exact component.
5. If ANY thread crashes, the Thread Monitor will instantly log a FATAL trace.
