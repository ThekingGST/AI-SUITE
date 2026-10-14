"""AI Action Registry for discovering and defining editor AI actions."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class ActionOutput(Enum):
    EXPLANATION = auto()
    CODE_SUGGESTION = auto()
    UNIT_TEST = auto()
    DOCUMENTATION = auto()


@dataclass
class AIAction:
    """Definition of an available AI Action."""
    id: str
    display_name: str
    icon: str
    description: str
    requires_selection: bool
    output_type: ActionOutput
    supported_languages: list[str] | None = None  # None means all


class AIActionRegistry:
    """Registry holding all supported AI code actions."""
    
    def __init__(self):
        self._actions: dict[str, AIAction] = {}
        self._register_default_actions()
        
    def _register_default_actions(self) -> None:
        actions = [
            AIAction("explain", "Explain Code", "help-circle", "Explain what this code does.", False, ActionOutput.EXPLANATION),
            AIAction("improve", "Improve Code", "zap", "Suggest improvements for better readability and performance.", True, ActionOutput.CODE_SUGGESTION),
            AIAction("refactor", "Refactor", "code", "Refactor the code structure without changing behavior.", True, ActionOutput.CODE_SUGGESTION),
            AIAction("fix_bug", "Fix Bug", "alert-triangle", "Identify and fix bugs in the code.", True, ActionOutput.CODE_SUGGESTION),
            AIAction("generate_tests", "Generate Tests", "check-circle", "Generate unit tests for this code.", True, ActionOutput.UNIT_TEST),
            AIAction("generate_docs", "Documentation", "file-text", "Generate docstrings and comments.", True, ActionOutput.DOCUMENTATION),
            AIAction("security_review", "Security Review", "shield", "Review code for security vulnerabilities.", False, ActionOutput.EXPLANATION),
            AIAction("optimize", "Optimize Performance", "activity", "Optimize the code for speed or memory.", True, ActionOutput.CODE_SUGGESTION),
        ]
        for action in actions:
            self.register(action)
            
    def register(self, action: AIAction) -> None:
        self._actions[action.id] = action
        
    def get_action(self, action_id: str) -> AIAction | None:
        return self._actions.get(action_id)
        
    def get_all_actions(self) -> list[AIAction]:
        return list(self._actions.values())
        
    def get_applicable_actions(self, has_selection: bool) -> list[AIAction]:
        """Filter actions based on whether the user has selected text."""
        return [a for a in self._actions.values() if not a.requires_selection or has_selection]


# Module-level singleton
action_registry = AIActionRegistry()
