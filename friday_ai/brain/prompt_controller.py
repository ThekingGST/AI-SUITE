"""Prompt Controller: Thin UI-facing controller delegating to AI Orchestrator."""

from __future__ import annotations

from PyQt5.QtCore import QObject

from friday_ai.brain.ai_orchestrator import AIOrchestrator
from friday_ai.core.signals import signals
from shared.logger import get_logger

LOG = get_logger("friday.prompt_controller")


class PromptController(QObject):
    """Thin UI delegate that listens to signals and passes them to the AI Orchestrator."""

    def __init__(
        self,
        orchestrator: AIOrchestrator,
        parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self.orchestrator = orchestrator
        self._connect_signals()

    def _connect_signals(self) -> None:
        signals.ai_prompt_submitted.connect(self._on_prompt)
        signals.ai_stop_requested.connect(self._on_stop)

    def _on_prompt(self, user_prompt: str, action: str) -> None:
        LOG.info("PromptController: Delegating prompt to AIOrchestrator.")
        self.orchestrator.submit_prompt(user_prompt, action)

    def _on_stop(self) -> None:
        LOG.info("PromptController: Delegating stop request to AIOrchestrator.")
        self.orchestrator.cancel_active()

