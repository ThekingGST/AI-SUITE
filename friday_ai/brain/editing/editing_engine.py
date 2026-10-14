"""Editing Engine: Transforms parsed AI responses into interactive ChangeSets."""

from __future__ import annotations
import uuid

from PyQt5.QtCore import QObject

from friday_ai.brain.ai_actions.response_parser import ResponseParser, ParsedAIResponse
from friday_ai.brain.ai_actions.action_context import AIActionRequest
from friday_ai.brain.editing.change_set import ChangeSet, EditOperation, ChangeType, EditStatus
from friday_ai.core.signals import signals
from shared.logger import get_logger

LOG = get_logger("friday.editing_engine")


class EditingEngine(QObject):
    """Coordinates the generation of structural changes from AI actions."""
    
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        signals.ai_action_finished.connect(self._on_action_finished)
        
    def _on_action_finished(self, request: AIActionRequest, final_text: str) -> None:
        """Process the output of an AI Action."""
        
        # Only process actions that are expected to yield code modifications
        # Explanation, Docs, or Security Review might not strictly replace code,
        # but if they return CODE_SUGGESTION, we process them.
        from friday_ai.brain.ai_actions.action_registry import ActionOutput
        
        if request.action.output_type not in (ActionOutput.CODE_SUGGESTION, ActionOutput.DOCUMENTATION, ActionOutput.UNIT_TEST):
            return

        parsed = ResponseParser.parse(final_text)
        
        if not parsed.code_blocks:
            LOG.info("EditingEngine: No code blocks detected in AI response.")
            return
            
        change_set = self._build_change_set(request, parsed)
        if change_set and change_set.operations:
            LOG.info("EditingEngine: Generated ChangeSet %s with %d operations", change_set.id, len(change_set.operations))
            
            # Since the preview dialog needs to be displayed, we must dispatch a signal
            # However, since we haven't defined diff_preview_requested yet, we will add it to signals
            
            # NOTE: We only emit the signal if we have something to apply.
            signals.diff_preview_requested.emit(change_set)
            
    def _build_change_set(self, request: AIActionRequest, parsed: ParsedAIResponse) -> ChangeSet | None:
        
        # We assume the AI returns the modified code in a single primary code block.
        # If there are multiple, we'll concatenate or take the largest/first one for this milestone.
        # Let's take the first one that matches the original file's language or just the first.
        
        primary_block = parsed.code_blocks[0]["content"]
        
        original_text = request.context.selected_text
        if not original_text:
            # If no selection, we assume it's attempting a full file replacement or it's a new file.
            # But the prompt says "Never modify files automatically... original_text replacement_text"
            # We don't have the full file content in context right now unless we fetch it.
            # To be safe, if there's no selection, we might not want to blind-replace.
            # But let's assume if selected_text is empty, it's adding to the bottom or replacing all.
            # Actually, `request.context.selected_text` should always be populated if `requires_selection` is true.
            pass
            
        op = EditOperation(
            original_text=original_text,
            replacement_text=primary_block,
            change_type=ChangeType.REPLACE if original_text else ChangeType.INSERT,
            status=EditStatus.PENDING
        )
        
        # Build session metrics info
        provider = ""
        model = ""
        for m in request.session.metrics_history:
            if m.request_id == request.request_id:
                provider = m.provider
                model = m.model
                break
                
        return ChangeSet(
            id=str(uuid.uuid4()),
            file_path=request.context.file_path,
            language=request.context.language,
            summary=f"{request.action.display_name} via {model}",
            operations=[op],
            source_action=request.action.id,
            provider=provider,
            model=model
        )
