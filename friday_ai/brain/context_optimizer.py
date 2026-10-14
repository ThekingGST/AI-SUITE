"""Context Optimizer: Decides what context should be included based on Task Intent."""

from __future__ import annotations
from dataclasses import dataclass
from friday_ai.brain.task_analyzer import TaskIntent


@dataclass
class ContextPlan:
    """Instructions for the ContextBuilder on what to include."""
    include_project_summary: bool = True
    include_runtime_env: bool = False
    include_recent_execution: bool = False
    include_current_file: bool = False
    include_selected_code: bool = False
    include_related_symbols: bool = False
    include_recent_files: bool = False


class ContextOptimizer:
    """Determines the optimal context plan based on intent."""
    
    def optimize(self, intent: TaskIntent, has_selection: bool = False) -> ContextPlan:
        """Return a ContextPlan tailored for the specific intent."""
        plan = ContextPlan()
        
        # We always want the project summary for general awareness
        plan.include_project_summary = True
        
        if intent == TaskIntent.CHAT or intent == TaskIntent.GENERAL_QUESTION:
            # Minimal context for general chat to save tokens
            pass
            
        elif intent == TaskIntent.EXPLANATION:
            plan.include_current_file = True
            plan.include_selected_code = has_selection
            plan.include_related_symbols = True
            
        elif intent == TaskIntent.REFACTORING or intent == TaskIntent.CODE_GENERATION:
            plan.include_current_file = True
            plan.include_selected_code = has_selection
            plan.include_related_symbols = True
            plan.include_recent_files = True
            
        elif intent == TaskIntent.DEBUGGING:
            plan.include_current_file = True
            plan.include_selected_code = has_selection
            plan.include_recent_execution = True
            plan.include_runtime_env = True
            plan.include_related_symbols = True
            
        elif intent == TaskIntent.ARCHITECTURE:
            plan.include_recent_files = True
            plan.include_related_symbols = True
            # Doesn't necessarily need the whole current file
            
        elif intent == TaskIntent.TEST_GENERATION:
            plan.include_current_file = True
            plan.include_selected_code = has_selection
            plan.include_related_symbols = True
            plan.include_runtime_env = True
            
        elif intent == TaskIntent.DOCUMENTATION:
            plan.include_current_file = True
            plan.include_selected_code = has_selection
            
        return plan
