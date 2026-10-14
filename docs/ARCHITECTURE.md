# System Architecture

AI Suite is designed to be a highly modular, decoupled application running on local hardware. This document outlines the fundamental architectural pillars.

## 1. Decoupled UI and Business Logic

The user interface (PyQt5) and the core AI intelligence run entirely independently.
They communicate exclusively through an asynchronous **Event Bus**.

```text
[ PyQt5 Main Thread ] <----(Event Bus)----> [ Background Worker Threads ]
```

This prevents the UI from freezing during intensive blocking operations (like LLM inference or audio TTS processing).

## 2. BootWorker Architecture

When AI Suite starts, it does not immediately load the heavy LLM models into RAM.
Instead, the `BootWorker` is spawned on a separate thread:
1. Displays the `BootOverlay`.
2. Validates Python environment and dependencies.
3. Initializes the EventBus.
4. Starts the `SessionManager` (SQLite).
5. Pre-warms the TTS and STT engines.
6. Connects to the local Ollama instance.
7. Triggers the cinematic UI dissolve into the active workspace.

For more details, see `BOOT_SYSTEM.md`.

## 3. Dependency Injection (DI)

To avoid circular dependencies, AI Suite uses a DI container (`ServiceContainer`). 
When a workspace is loaded, it is handed a dictionary of shared services (e.g., `AssistantManager`, `ModelManager`), allowing it to act on the system without importing modules directly.

## 4. Model Provider Factory

AI Suite is LLM-agnostic. The `ProviderFactory` abstracts the generation pipeline.
- `OllamaProvider`: Communicates with local `llama3` instances.
- `OpenRouterProvider`: Communicates with cloud APIs when required by specific workspaces (e.g., FRIDAY).

## 5. Vision and Screen Context

Workspaces like JARVIS can "see" the screen. 
This is handled by a background screenshot loop that processes frames through a YOLO (You Only Look Once) object detection model, turning raw pixels into a textual context vector that is appended to the LLM prompt.
