"""Application-wide event bus for FRIDAY.

UI components communicate through this signal hub instead of calling each
other directly.  This ensures loose coupling: the file explorer doesn't need
to know about the editor — it emits ``file_open_requested`` and the editor
subscribes.

Usage::

    from friday_ai.core.signals import signals

    # Emitter
    signals.file_open_requested.emit("/path/to/file.py")

    # Subscriber
    signals.file_open_requested.connect(self._on_file_requested)
"""

from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal as Signal


class AppSignals(QObject):
    """Singleton signal bus for cross-component communication.

    Every signal represents an application-level event.  Components emit
    signals to announce state changes; other components subscribe to react.
    """

    # ── File events ──────────────────────────────────────────────────────
    file_new_requested = Signal(str)    # Request to create a new file (type)
    file_open_requested = Signal(str)   # Request to open a file (path)
    file_opened = Signal(str)           # File was opened in editor (path)
    file_closed = Signal(str)           # File was closed (path)
    file_saved = Signal(str)            # File was saved (path)
    goto_line_requested = Signal(int, int) # (line, col)

    # ── Problem events ───────────────────────────────────────────────────
    problems_updated = Signal(list)     # list[Problem]

    # ── Tab events ───────────────────────────────────────────────────────
    tab_changed = Signal(int)           # Tab index
    tab_close_requested = Signal(int)   # Tab index

    # ── Workspace events ─────────────────────────────────────────────────
    workspace_switched = Signal(str)    # "jarvis" | "friday" | "edith"
    project_open_requested = Signal(str) # User wants to open a folder (path)
    project_opened = Signal(str)        # Project was validated and opened
    project_closed = Signal()
    project_stats = Signal(str, int)    # (project_name, file_count)

    # ── Mission Control events ───────────────────────────────────────────
    mission_update = Signal(str, str)   # (phase, message)
    mission_clear = Signal()

    # ── Status bar events ────────────────────────────────────────────────
    status_message = Signal(str)        # Transient status text
    cursor_position = Signal(int, int)  # (line, column)

    # ── Run events ───────────────────────────────────────────────────────
    run_file_requested = Signal(str)    # Request to run a file (path)
    run_compile_started = Signal(str)   # Compilation started (file)
    run_compile_finished = Signal(str, int) # Compilation finished (file, code)
    run_stop_requested = Signal()       # Request to stop current run
    compiler_updated = Signal(str)      # Compiler/interpreter path

    # ── Project events (Milestone 4) ─────────────────────────────────────
    project_create_requested = Signal()           # Trigger project wizard
    project_created = Signal(str)                 # Project was created (path)
    project_type_detected = Signal(str, str)      # (path, project_type)

    # ── Toolchain events (Milestone 4) ───────────────────────────────────
    toolchains_updated = Signal()                 # Toolchain scan completed

    # ── Environment events (Milestone 4) ─────────────────────────────────
    environment_changed = Signal(str, str)        # (env_name, interpreter_path)
    environment_created = Signal(str)             # env_path
    environment_removed = Signal(str)             # env_path
    package_installed = Signal(str, str)          # (name, version)

    # ── Build events (Milestone 4) ───────────────────────────────────────
    build_started = Signal(str)                   # file_path
    build_finished = Signal(str, int)             # file_path, exit_code
    build_output = Signal(str, str)               # text, category

    # ── Execution events (Milestone 4) ───────────────────────────────────
    run_project_requested = Signal()              # Run the project's main file
    execution_completed = Signal(object)          # ExecutionEvent

    # ── AI events ────────────────────────────────────────────────────────
    ai_prompt_submitted = Signal(str, str)    # (prompt, action)
    ai_chunk_received = Signal(str)           # streaming text chunk
    ai_response_complete = Signal(str)        # full response
    ai_error = Signal(str)                    # error message
    ai_busy = Signal(bool)                    # True when processing
    ai_model_changed = Signal(str, str)       # (provider, model)
    ai_stop_requested = Signal()              # cancel generation
    ai_action_requested = Signal(object)      # AIActionRequest
    ai_action_finished = Signal(object, str)  # (AIActionRequest, final_text)
    diff_preview_requested = Signal(object)   # ChangeSet
    diff_apply_requested = Signal(object)     # ChangeSet
    selection_changed = Signal(str)           # selected text in editor
    search_requested = Signal(str)            # search query


# Module-level singleton — import ``signals`` from anywhere.
signals = AppSignals()
