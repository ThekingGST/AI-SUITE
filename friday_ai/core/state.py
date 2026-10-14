"""Workspace state persistence for the AI Suite.

Saves and restores panel sizes, active tab, scroll positions, etc. so that
switching between JARVIS / FRIDAY / EDITH workspaces feels instant rather
than destructive.

Phase 1 implementation: in-memory only.  Future phases will persist to disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkspaceState:
    """Snapshot of a workspace's UI state."""

    name: str
    splitter_sizes: list[int] = field(default_factory=list)
    active_tab_index: int = 0
    open_files: list[str] = field(default_factory=list)
    mission_log: list[str] = field(default_factory=list)


class StateManager:
    """Manages workspace state snapshots.

    Usage::

        state_mgr = StateManager()
        state_mgr.save("friday", current_state)
        restored = state_mgr.restore("friday")
    """

    def __init__(self) -> None:
        self._states: dict[str, WorkspaceState] = {}

    def save(self, name: str, state: WorkspaceState) -> None:
        """Persist a workspace state snapshot."""
        self._states[name] = state

    def restore(self, name: str) -> WorkspaceState | None:
        """Retrieve a previously saved workspace state."""
        return self._states.get(name)

    def has(self, name: str) -> bool:
        """Check whether a snapshot exists for *name*."""
        return name in self._states
