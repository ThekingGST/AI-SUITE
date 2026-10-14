"""Apply Engine: Validates and applies changes using Qt's native undo stack."""

from __future__ import annotations
from PyQt5.QtGui import QTextCursor, QTextDocument
from PyQt5.QtWidgets import QPlainTextEdit

from friday_ai.brain.editing.change_set import ChangeSet, EditStatus, ChangeType
from shared.logger import get_logger

LOG = get_logger("friday.apply_engine")


class ApplyEngine:
    """Safely applies EditOperations to a QPlainTextEdit."""
    
    def __init__(self, editor: QPlainTextEdit):
        self.editor = editor
        
    def apply(self, change_set: ChangeSet) -> bool:
        """Apply all pending operations in a changeset safely.
        
        Returns:
            True if all pending edits applied successfully, False if aborted.
        """
        
        # Validation Pass (No mutation)
        for op in change_set.operations:
            if op.status != EditStatus.PENDING:
                continue
                
            if op.change_type in (ChangeType.REPLACE, ChangeType.DELETE):
                if not op.original_text:
                    continue
                # 1 & 2: Verification is implicit if we have the editor
                # 3 & 4: original_text matches
                # We need to find the exact text in the document
                document = self.editor.document()
                text = document.toPlainText()
                
                # Check if it exists exactly once, or at least exists
                if op.original_text not in text:
                    LOG.error("Validation failed: Original text not found in document.")
                    op.status = EditStatus.FAILED
                    return False
                    
        # Application Pass (Mutation wrapped in undo block)
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        
        success = True
        try:
            for op in change_set.operations:
                if op.status != EditStatus.PENDING:
                    continue
                    
                document = self.editor.document()
                
                if op.change_type == ChangeType.INSERT:
                    # In absence of location info, inserts are difficult if original_text is empty.
                    # Usually, AI suggestions either replace or delete.
                    # If it's a raw insert without original context, it's unsafe.
                    pass
                else:
                    # Replace or Delete
                    # Find the text
                    # To be robust, we find the first occurrence. 
                    # If `selection_hash` existed, we could be smarter, but simple text search is the starting point.
                    text = document.toPlainText()
                    start_idx = text.find(op.original_text)
                    if start_idx != -1:
                        # Convert string index to cursor position
                        cursor.setPosition(start_idx)
                        cursor.setPosition(start_idx + len(op.original_text), QTextCursor.MoveMode.KeepAnchor)
                        
                        if op.change_type == ChangeType.DELETE:
                            cursor.removeSelectedText()
                        else:
                            cursor.insertText(op.replacement_text)
                            
                        op.status = EditStatus.APPLIED
                    else:
                        op.status = EditStatus.FAILED
                        success = False
        except Exception as e:
            LOG.error("Failed during apply block: %s", e)
            success = False
        finally:
            cursor.endEditBlock()
            
        return success
