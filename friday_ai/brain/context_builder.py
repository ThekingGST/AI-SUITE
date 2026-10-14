"""Context builder for AI prompts.

Assembles the full context (selected code, current file, related symbols, etc.)
before sending it to the Provider Manager.
"""

from __future__ import annotations
from pathlib import Path

from friday_ai.brain.project_brain import ProjectBrain
from friday_ai.brain.workspace_context import WorkspaceContext
from shared.logger import get_logger

LOG = get_logger("friday.context_builder")


class ContextBuilder:
    """Builds structured prompt context for the AI."""

    def __init__(self, brain: ProjectBrain, workspace: WorkspaceContext) -> None:
        self.brain = brain
        self.workspace = workspace

    def build_system_prompt(self, user_prompt: str, action: str = "", metrics=None, plan=None) -> str:
        """Build the full system context string."""
        import time
        t0 = time.time() * 1000.0
        state = self.workspace.get_context()
        
        # If no plan provided, assume everything is True (backward compatibility)
        if plan is None:
            from friday_ai.brain.context_optimizer import ContextPlan
            plan = ContextPlan(
                include_project_summary=True,
                include_runtime_env=True,
                include_recent_execution=True,
                include_current_file=True,
                include_selected_code=True,
                include_related_symbols=True,
                include_recent_files=True
            )
        
        parts = [
            "You are FRIDAY, an expert AI software engineer built into a professional IDE.",
            "Always output concise, production-ready code.",
            "Format your responses in markdown.",
            ""
        ]

        # 1. Project Summary
        if plan.include_project_summary and state.current_project:
            proj_name = Path(state.current_project).name
            parts.append(f"## Project: {proj_name}")
            if getattr(state, "project_type", None):
                parts.append(f"- Type: {state.project_type}")
            if self.brain.index:
                file_count = len(self.brain.index.files)
                parts.append(f"- Files: {file_count} indexed")
            parts.append("")

        # 1.5 Runtime Environment
        if plan.include_runtime_env and (getattr(state, "active_runtime", None) or getattr(state, "active_environment", None)):
            parts.append("## Runtime Environment")
            if getattr(state, "active_runtime", None):
                parts.append(f"- Runtime: {state.active_runtime}")
            if getattr(state, "active_environment", None):
                parts.append(f"- Environment: {state.active_environment}")
            if getattr(state, "active_interpreter", None):
                parts.append(f"- Interpreter: {state.active_interpreter}")
            parts.append("")

        # 1.6 Recent Execution
        if plan.include_recent_execution and getattr(state, "last_execution_exit_code", None) is not None:
            parts.append("## Recent Execution Result")
            parts.append(f"- Exit Code: {state.last_execution_exit_code}")
            if getattr(state, "last_execution_output", ""):
                parts.append("```text")
                parts.append(state.last_execution_output)
                parts.append("```")
            parts.append("")
            
        t1 = time.time() * 1000.0
        if metrics:
            metrics.context_breakdown["workspace_ms"] = t1 - t0

        # 2. Current File & Selection
        if plan.include_current_file and state.current_file:
            current_path = Path(state.current_file)
            parts.append(f"## Current File: {current_path.name}")
            t_io = time.time() * 1000.0
            try:
                content = current_path.read_text(encoding="utf-8")
                parts.append("```" + (state.active_language or "").lower())
                parts.append(content)
                parts.append("```\n")
            except Exception:
                parts.append("(File content unavailable)\n")
            if metrics:
                metrics.context_breakdown["file_io_ms"] = (time.time() * 1000.0) - t_io
                
        # 3. Selected Code
        if plan.include_selected_code and state.selected_code:
            parts.append("## User Selection")
            parts.append("The user has selected the following code:")
            parts.append("```" + (state.active_language or "").lower())
            parts.append(state.selected_code)
            parts.append("```\n")
                
        # 4. Related Symbols & Imports
        if plan.include_related_symbols and state.current_file:
            t_brain = time.time() * 1000.0
            related = self.brain.find_related_symbols(state.current_file)
            if related:
                parts.append("## Related Symbols (Imported)")
                for sym in related[:5]:  # Limit to top 5 to avoid context bloat
                    parts.append(f"- `{sym.name}` ({sym.kind}) in `{Path(sym.file_path).name}`")
                    if sym.signature:
                        parts.append(f"  Signature: `{sym.signature}`")
                parts.append("")
            if metrics:
                metrics.context_breakdown["project_brain_ms"] = (time.time() * 1000.0) - t_brain

        # 5. Recent Files
        if plan.include_recent_files and state.recent_files:
            parts.append("## Recent Files")
            for f in state.recent_files[:3]:
                if f != state.current_file:
                    parts.append(f"- {Path(f).name}")
            parts.append("")

        return "\n".join(parts)

    def build_user_prompt(self, prompt: str, action: str = "") -> str:
        """Format the user's prompt based on the chosen action."""
        if not action:
            return prompt
            
        state = self.workspace.get_context()
        target = "the selected code" if state.selected_code else "the current file"
        
        if action == "explain":
            return f"Please explain {target}. Focus on its purpose and how it works.\n\nAdditional context: {prompt}"
        elif action == "refactor":
            return f"Please refactor {target} to improve its structure and readability.\n\nAdditional instructions: {prompt}"
        elif action == "fix":
            return f"Please find and fix any bugs in {target}.\n\nAdditional context: {prompt}"
        elif action == "document":
            return f"Please generate docstrings and comments for {target}.\n\nAdditional instructions: {prompt}"
        elif action == "optimize":
            return f"Please optimize {target} for better performance.\n\nAdditional instructions: {prompt}"
        elif action == "generate":
            return f"Please generate code based on the following requirements:\n\n{prompt}"
            
        return prompt
