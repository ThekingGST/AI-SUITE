# The Boot System

The AI Suite Boot System is designed to create a continuous, cinematic startup experience without freezing the main UI thread while heavy backend services initialize.

## Continuous Boot Architecture

AI Suite uses a single-window architecture (`AISuiteWindow`) which starts in `boot_mode=True`. 
During this phase, the main dashboard UI is completely hidden (opacity 0.0), and a lightweight overlay (`BootOverlay`) is placed on top.

### Components

1. **`BootOverlay`**: A purely visual `QWidget` containing the Arc Reactor animations and status text. It knows nothing about backend services.
2. **`BootWorker`**: A `QThread` subclass that safely initializes SQLite databases, Ollama connections, and TTS models in the background.
3. **`BootController`**: The orchestrator that lives on the main thread. It connects the signals from the `BootWorker` to the visual updates of the `BootOverlay`.

## The Sequence

1. `main.py` creates `QApplication` and `AISuiteWindow`.
2. `BootController` is instantiated and starts `BootWorker`.
3. As `BootWorker` initializes systems (Event Bus, Managers, Models), it emits milestone signals.
4. `BootOverlay` updates its text and visual stages based on these milestones.
5. When `BootWorker` is finished, `BootOverlay` begins its final transition.
6. The Boot Overlay shrinks and fades out while simultaneously triggering the progressive reveal of the underlying main dashboard UI.
7. `BootOverlay` emits `transition_complete` and is cleanly removed from the layout via `deleteLater()`.

This architecture prevents any QObject/Thread affinity warnings by strictly isolating object creation to the correct threads and passing data only via Qt Signals and Slots.
