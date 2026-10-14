"""Preview Generator: Pure backend logic for generating diff strings."""

from __future__ import annotations
import difflib

from friday_ai.brain.editing.change_set import ChangeSet, ChangeType, EditStatus


class PreviewGenerator:
    """Generates unified diff strings for UI consumption."""
    
    @staticmethod
    def generate_unified_diff(change_set: ChangeSet) -> str:
        """Generates a text-based unified diff from all pending operations."""
        lines = []
        
        for op in change_set.operations:
            if op.status != EditStatus.PENDING:
                continue
                
            original_lines = op.original_text.splitlines(keepends=True) if op.original_text else []
            replacement_lines = op.replacement_text.splitlines(keepends=True) if op.replacement_text else []
            
            # If the texts are exactly the same, no diff needed
            if op.original_text == op.replacement_text:
                continue
                
            diff = list(difflib.unified_diff(
                original_lines,
                replacement_lines,
                fromfile="Original",
                tofile="Suggested",
                n=3  # Context lines
            ))
            
            if diff:
                lines.extend(diff)
                lines.append("\n")
                
        return "".join(lines)
