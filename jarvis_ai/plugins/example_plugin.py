from __future__ import annotations

from jarvis_ai.plugins.registry import PluginCommand, PluginRegistry


def register(registry: PluginRegistry) -> None:
    """Example plugin registration function for future modules."""

    registry.register(
        PluginCommand(
            name="diagnostic_ping",
            patterns=("diagnostic ping", "jarvis diagnostic"),
            handler=lambda _: "Diagnostic channel is responsive.",
            priority=40,
        )
    )
