# JARVIS AI Desktop Assistant

JARVIS is a local-first Windows desktop assistant built with Python and PyQt5. It combines a cinematic hologram interface, offline voice recognition, text-to-speech, local Ollama chat, webcam vision, face recognition, object detection, emotion detection, gesture controls, persistent memory, file search, and system automation.

The app is designed to run without API keys. Model-powered systems use local files and degrade safely when a model is not installed yet.

## Quick Start on Windows 10/11

1. Install Python 3.11.
2. During installation, enable **Add python.exe to PATH**.
3. Open PowerShell in this folder.
4. Create a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel setuptools
pip install -r .\jarvis_ai\requirements.txt
```

5. Run the assistant:

```powershell
python .\jarvis_ai\main.py
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Optional Ollama Brain

1. Install Ollama from `https://ollama.com`.
2. Restart PowerShell.
3. Pull one local model:

```powershell
ollama pull llama3
```

JARVIS automatically checks `llama3`, `mistral`, then `phi`. If Ollama is not running, it uses its offline command brain and deterministic fallback responses.

## Model Download Guide

Place these files in `jarvis_ai/models/`:

| Feature | Required file/folder | Source |
| --- | --- | --- |
| Vosk speech recognition | `vosk-model/` | Download a small English Vosk model from `https://alphacephei.com/vosk/models` and extract it as this folder. |
| Face detection | `deploy.prototxt` and `res10_300x300_ssd_iter_140000.caffemodel` | OpenCV SSD face detector model. |
| Face recognition | `face_recognition_sface_2021dec.onnx` | OpenCV Zoo SFace ONNX model. |
| Object detection | `yolov8n.pt` | Download with Ultralytics or from the official YOLOv8 release assets. |

The app still launches if these are missing. The affected feature logs a clear warning and stays disabled instead of crashing.

### Vosk Setup

1. Open `https://alphacephei.com/vosk/models`.
2. Download a small English model, for example `vosk-model-small-en-us`.
3. Extract the ZIP.
4. Rename the extracted folder to `vosk-model`.
5. Place it at `jarvis_ai/models/vosk-model/`.

### YOLO Setup

Install dependencies first, then download YOLOv8n with:

```powershell
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
move .\yolov8n.pt .\jarvis_ai\models\yolov8n.pt
```

### SFace Setup

Download `face_recognition_sface_2021dec.onnx` from the OpenCV Zoo SFace model page and place it in `jarvis_ai/models/`.

### OpenCV Face Detector Setup

Download:

- `deploy.prototxt`
- `res10_300x300_ssd_iter_140000.caffemodel`

Place both in `jarvis_ai/models/`.

## Voice Commands

Wake word: `Jarvis`

Examples:

- `Jarvis open notepad`
- `Jarvis open my DBMS notes`
- `Jarvis what do you see`
- `Jarvis remember my favorite game is Valorant`
- `Jarvis what is my favorite game`
- `Jarvis take screenshot`
- `Jarvis system status`
- `Jarvis tell me a joke`
- `Jarvis play lo-fi music`

You can also type commands directly into the AI console, which is useful before the Vosk model or microphone is configured.

## Face Registration

The project includes the SFace registration pipeline. A future UI button can call it directly. For now, registration is available through code:

```python
frame = camera.latest_frame()
faces = camera.vision.face_detector.detect(frame)
if faces:
    camera.vision.face_recognizer.register_owner(frame, faces[0])
```

After registration, embeddings are saved to `jarvis_ai/data/owner_embeddings.json`. Unknown faces are captured in `jarvis_ai/data/intruders/`.

## Architecture

```text
jarvis_ai/
  main.py                  Application entry point
  config.py                Central paths and runtime settings
  voice/                   Vosk listener, wake word, TTS, routing
  ai/                      Ollama brain, memory, personality, context
  vision/                  Camera, faces, SFace, YOLO, DeepFace, MediaPipe
  automation/              Apps, files, system control, utilities
  ui/                      PyQt5 hologram interface and widgets
  core/                    Worker primitives and singleton model manager
  plugins/                 Dynamic command plugin registration
  utils/                   Logging, constants, helper functions
```

## System Design

- PyQt5 main thread only renders UI and handles signals.
- Camera capture runs in `CameraSystem`, a dedicated cancellable worker.
- Face recognition, object detection, emotion detection, and gesture processing run in `VisionWorker`.
- Camera frames use a latest-only queue so slow inference never builds a memory backlog.
- Speech synthesis uses a queue-based `Speaker`.
- Voice recognition runs in `VoiceListener`.
- Commands are processed on a background command loop, not in the UI thread.
- Models are cached in `ModelManager` to avoid duplicate loading.
- Shutdown stops listener, camera, vision worker, and speaker cleanly.
- The command router uses hard commands and plugin commands before LLM fallback.

## Performance Notes

- Camera capture runs on its own thread.
- Heavy vision inference runs on a separate worker thread.
- Speech synthesis uses a queue and a dedicated worker thread.
- Voice recognition runs continuously in the background.
- UI updates use Qt timers and never block on AI inference.
- File indexing runs in a background thread and refreshes periodically.
- Vision models are loaded once and reused.
- Emotion detection is throttled because DeepFace is heavier than object and face detection.
- Gesture actions use cooldowns to prevent repeated triggers.

## Error Handling

JARVIS handles:

- Missing webcam
- Missing microphone or PyAudio device errors
- Missing Vosk, YOLO, SFace, face detector, or DeepFace dependencies
- Ollama not installed or not running
- Internet failures for web commands
- File permission errors while indexing or cleaning temp files
- Camera release during shutdown

Failures are written to `jarvis_ai/data/jarvis.log`.

## Troubleshooting

### `python` is not recognized

Reinstall Python 3.11 and enable **Add python.exe to PATH**. Then open a new PowerShell window.

### PyAudio installation fails

Install pip tooling first:

```powershell
python -m pip install --upgrade pip wheel setuptools
pip install PyAudio
```

If it still fails, install the Microsoft C++ Build Tools or use a Python 3.11 PyAudio wheel.

### Microphone does not work

- Check Windows privacy settings for microphone access.
- Confirm your default input device works in Windows Sound Settings.
- Make sure `jarvis_ai/models/vosk-model/` exists.

### Camera is black or unavailable

- Close other apps using the webcam.
- Check Windows camera privacy settings.
- Change `camera_index` in `config.py` from `0` to `1`.

### Ollama responses do not work

Run:

```powershell
ollama list
ollama pull llama3
```

Then restart JARVIS.

### App feels slow

- Keep object detection disabled until needed.
- Use `yolov8n.pt`, not a larger YOLO model.
- Close GPU-heavy games while demonstrating.
- Use a smaller Vosk model.
- Disable DeepFace emotion detection in `CameraSystem` if your CPU is low-end.

## Face Recognition

Face detection uses OpenCV DNN SSD. Face recognition uses ONNX Runtime for the SFace embedding pipeline and cosine similarity for owner matching. Owner embeddings are stored in `jarvis_ai/data/owner_embeddings.json`.

To register an owner face from code or a future UI button, call:

```python
camera.face_recognizer.register_owner(frame, face_box)
```

Unknown faces are saved to `jarvis_ai/data/intruders/` when owner embeddings exist.

## Gesture Controls

MediaPipe Hands maps simple gestures to desktop actions:

- Open hand: play/pause
- Closed fist: screenshot
- Two fingers: volume up
- Index finger: volume down

Cooldown protection prevents repeated accidental triggers.

## Plugin System

Plugins register commands dynamically through `PluginRegistry`. A plugin should expose a `register(registry)` function and add one or more `PluginCommand` objects.

Example:

```python
from plugins.registry import PluginCommand

def register(registry):
    registry.register(
        PluginCommand(
            name="smart_light",
            patterns=("turn on lights", "lights on"),
            handler=lambda text: "Smart lights activated.",
            priority=25,
        )
    )
```

Command priority is lower-first. Built-in system commands use high priority, while AI fallback happens last. This design allows future modules such as smart home, OCR, Discord, IoT, custom voice packs, sensors, and automation workflows without rewriting the core router.

## Beginner Workflow

1. Install Python 3.11.
2. Create and activate `.venv`.
3. Install `requirements.txt`.
4. Launch once without models to confirm the UI opens.
5. Add Vosk for wake-word voice commands.
6. Add Ollama and `llama3` for local chat.
7. Add YOLO for object detection.
8. Add face detector and SFace for identity recognition.
9. Test typed commands first.
10. Test voice commands with `Jarvis open notepad`.
11. Enable object detection from the UI only when demonstrating.
12. Review `jarvis_ai/data/jarvis.log` when something does not work.

## Notes for Demonstrations

For the most impressive demo, install the Vosk model, YOLOv8n, OpenCV face detector, SFace ONNX, and run Ollama with `llama3`. The app remains functional without them, but the cinematic vision and voice systems become much stronger once the local assets are present.
