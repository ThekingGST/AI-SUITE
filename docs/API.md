# Developer API Reference

AI Suite is built on a modular Event-Driven architecture using Dependency Injection. This document outlines the core APIs that workspace developers and contributors should be familiar with.

## Dependency Injection (DI) Container

The `ServiceContainer` manages all shared resources (Managers, Models, UI overlays).

```python
from ai_suite.core.registry import ServiceContainer

# Registering a service
container = ServiceContainer()
container.register("assistant_manager", AssistantManager(event_bus))

# Retrieving a service
am = container.get("assistant_manager")
```

## The Event Bus

The `EventBus` is the central nervous system of AI Suite. Modules should rarely call each other directly; instead, they emit and listen to events.

### Subscribing to Events

```python
from ai_suite.core.events import EventBus, Event

def on_user_spoke(event: Event):
    print(f"User said: {event.payload['text']}")

event_bus.subscribe("user_spoke", on_user_spoke)
```

### Emitting Events

```python
event_bus.publish(Event(
    type="ai_response_start",
    payload={"workspace": "jarvis"}
))
```

## Creating a Custom Workspace

To add a new workspace, you must create a class that inherits from `BaseWorkspace` and implements its lifecycle methods.

```python
from ai_suite.ui.workspace.base_workspace import BaseWorkspace

class CustomWorkspace(BaseWorkspace):
    def __init__(self, services: dict):
        super().__init__(workspace_id="custom", name="Custom AI")
        self.services = services
        
    def setup_ui(self):
        # Build your Qt UI here
        pass
        
    def on_activate(self):
        # Triggered when the user switches to this workspace
        pass
        
    def on_deactivate(self):
        # Triggered when the user switches away
        pass
```

Then, register it with the `WorkspaceManager`:

```python
workspace_manager.register_workspace(CustomWorkspace(services))
```

## Voice Pipeline API

The Voice pipeline uses cooperative cancellation to interrupt TTS when the user speaks.

- `voice_capture_started`: Emitted when Vosk detects speech.
- `user_spoke`: Emitted when Vosk finalizes transcription.
- `ai_response_start`: Emitted when the AI begins speaking (used to duck system volume or update UI).

For more detailed implementation details on specific modules, refer to `ARCHITECTURE.md`.
