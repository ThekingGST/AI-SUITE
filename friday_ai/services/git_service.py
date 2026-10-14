"""Lightweight Git information service.

Detects current branch name only. No git operations (commit, push, pull).
Those are out of scope for Milestone 2.
"""
from __future__ import annotations
from pathlib import Path
from PyQt5.QtCore import QObject
from shared.logger import get_logger

LOG = get_logger("friday.git")


class GitService(QObject):
    """Read-only git information."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project_root: str = ""

    def set_project_root(self, path: str) -> None:
        self._project_root = path

    def get_branch(self) -> str:
        """Return the current git branch name, or empty string."""
        if not self._project_root:
            return ""
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        
        intel = ServiceContainer.get(IntelligenceService)
        if not intel:
            return ""
            
        report = intel.inspect("git", repo_path=self._project_root)
        if report.status.value == "unknown":
            return ""
        return report.details.get("branch", "")

    def get_changed_files_count(self) -> int:
        """Return the number of changed files, or 0."""
        if not self._project_root:
            return 0
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        
        intel = ServiceContainer.get(IntelligenceService)
        if not intel:
            return 0
            
        report = intel.inspect("git", repo_path=self._project_root)
        return int(report.metrics.get("changed_files", 0))

    def is_git_repo(self) -> bool:
        """Check if the project root is a git repository."""
        if not self._project_root:
            return False
        return (Path(self._project_root) / ".git").exists()
