"""Diff Engine: Prepares structural diffs for inline application."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto


class ChangeType(Enum):
    ADDITION = auto()
    DELETION = auto()
    MODIFICATION = auto()


@dataclass
class DiffProposal:
    """Represents a proposed change to a specific file."""
    original_text: str
    suggested_text: str
    language: str
    file_path: str
    change_type: ChangeType
    summary: str


class DiffEngine:
    """Scaffolding for future inline preview and application of edits."""
    
    @staticmethod
    def create_proposal(
        original: str, 
        suggested: str, 
        file_path: str, 
        language: str = ""
    ) -> DiffProposal:
        """Create a diff proposal comparing original to suggested text."""
        
        # In the future, this will perform a structural diff or block matching.
        # For now, it simply encapsulates the raw string swap.
        
        if not original:
            change_type = ChangeType.ADDITION
        elif not suggested:
            change_type = ChangeType.DELETION
        else:
            change_type = ChangeType.MODIFICATION
            
        summary = f"{change_type.name.capitalize()} in {file_path}"
        
        return DiffProposal(
            original_text=original,
            suggested_text=suggested,
            language=language,
            file_path=file_path,
            change_type=change_type,
            summary=summary
        )
