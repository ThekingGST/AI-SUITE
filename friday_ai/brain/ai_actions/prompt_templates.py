"""Prompt templates for AI Actions.

Decouples prompt engineering from business logic.
"""

from __future__ import annotations
from friday_ai.brain.ai_actions.action_context import ActionContext


def build_action_prompt(action_id: str, context: ActionContext) -> str:
    """Build a structured prompt tailored to the requested action."""
    
    # 1. Base formatting
    if context.selected_text:
        target = "the selected code"
        code_block = f"```\n{context.selected_text}\n```\n"
    else:
        target = "this file"
        code_block = ""
        
    prompt = f"Please `{action_id}` {target}.\n\n"
    
    # 2. Action-specific instructions
    if action_id == "explain":
        prompt += "Provide a clear, concise explanation of what the code does and how it works. Use bullet points for key steps if helpful."
    elif action_id == "improve":
        prompt += "Suggest improvements for better readability, maintainability, and following best practices. Provide the refactored code."
    elif action_id == "refactor":
        prompt += "Refactor the code to improve its internal structure without changing its external behavior. Provide the refactored code."
    elif action_id == "fix_bug":
        prompt += "Identify potential bugs or logical errors in the code. Explain the issue and provide the corrected code."
    elif action_id == "generate_tests":
        prompt += "Write comprehensive unit tests for this code. Cover edge cases and common scenarios."
    elif action_id == "generate_docs":
        prompt += "Generate comprehensive documentation (docstrings) for this code following standard language conventions."
    elif action_id == "optimize":
        prompt += "Analyze the performance of this code. Suggest and implement optimizations for speed or memory usage."
    elif action_id == "security_review":
        prompt += "Review the code for any potential security vulnerabilities, edge-case risks, or unsafe operations."
    else:
        prompt += "Provide a response addressing the code provided."

    # 3. Append the code block
    if code_block:
        prompt += f"\n\nHere is {target}:\n{code_block}"
        
    return prompt
