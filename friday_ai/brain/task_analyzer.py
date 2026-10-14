"""Task Analyzer: Classifies user intent to drive routing and context decisions."""

from __future__ import annotations
from enum import Enum, auto
from typing import Protocol


class TaskIntent(Enum):
    """The classified intent of a user prompt."""
    CHAT = auto()
    CODE_GENERATION = auto()
    EXPLANATION = auto()
    REFACTORING = auto()
    DEBUGGING = auto()
    DOCUMENTATION = auto()
    TEST_GENERATION = auto()
    ARCHITECTURE = auto()
    GENERAL_QUESTION = auto()


class TaskAnalyzer(Protocol):
    """Interface for classifying user tasks."""
    def analyze(self, user_prompt: str, action: str = "") -> TaskIntent:
        ...


class RuleBasedTaskAnalyzer:
    """A lightweight, zero-latency deterministic classifier."""
    
    def analyze(self, user_prompt: str, action: str = "") -> TaskIntent:
        """Analyze the prompt and IDE action to determine intent."""
        # 1. Action-based classification is the strongest signal
        if action == "explain":
            return TaskIntent.EXPLANATION
        if action in ("refactor", "improve", "optimize"):
            return TaskIntent.REFACTORING
        if action in ("fix", "fix_bug"):
            return TaskIntent.DEBUGGING
        if action in ("document", "generate_docs"):
            return TaskIntent.DOCUMENTATION
        if action == "generate_tests":
            return TaskIntent.TEST_GENERATION
        if action == "security_review":
            return TaskIntent.EXPLANATION
        if action == "generate":
            return TaskIntent.CODE_GENERATION

        # 2. Keyword heuristic for empty actions (free-form chat)
        lower_prompt = user_prompt.lower()
        
        # Test Generation
        if "write a test" in lower_prompt or "unit test" in lower_prompt:
            return TaskIntent.TEST_GENERATION
            
        # Code Generation
        if "create a " in lower_prompt or "write a " in lower_prompt or "implement" in lower_prompt:
            if "function" in lower_prompt or "class" in lower_prompt or "script" in lower_prompt:
                return TaskIntent.CODE_GENERATION
                
        # Debugging
        if "error" in lower_prompt or "exception" in lower_prompt or "bug" in lower_prompt or "why does it fail" in lower_prompt:
            return TaskIntent.DEBUGGING
            
        # Architecture
        if "architecture" in lower_prompt or "design pattern" in lower_prompt or "structure" in lower_prompt:
            return TaskIntent.ARCHITECTURE
            
        # General / Chat fallback
        if len(user_prompt.split()) < 5 and "?" not in user_prompt:
            return TaskIntent.CHAT
            
        return TaskIntent.GENERAL_QUESTION
