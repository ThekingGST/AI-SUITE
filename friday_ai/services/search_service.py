"""Project-wide file content search.

Searches files across the project on a background thread.
Respects skip-dirs to avoid searching node_modules, .git, etc.
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal as Signal
from friday_ai.core.workers import BackgroundWorker
from shared.logger import get_logger

LOG = get_logger("friday.search")

_SKIP_DIRS = frozenset({
    ".git", ".svn", "__pycache__", "node_modules", ".venv",
    "venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", "target", "bin", "obj", ".idea", ".vs",
})

_TEXT_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".md", ".rst", ".txt", ".csv",
    ".java", ".kt", ".c", ".cpp", ".h", ".hpp", ".cs",
    ".go", ".rs", ".rb", ".php", ".swift", ".sql",
    ".sh", ".bash", ".ps1", ".bat", ".cmd",
    ".xml", ".svg", ".env", ".gitignore",
})

_MAX_FILE_SIZE = 1_000_000  # 1 MB


@dataclass
class SearchMatch:
    """A single search result."""
    file_path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int


class SearchService(QObject):
    """Background file content search."""
    results_ready = Signal(list)  # list[SearchMatch]
    search_started = Signal()
    search_finished = Signal(int)  # total matches

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: BackgroundWorker | None = None
        self._project_root: str = ""

    def set_project_root(self, path: str) -> None:
        self._project_root = path

    def search(self, query: str, case_sensitive: bool = False) -> None:
        if not query or not self._project_root:
            self.results_ready.emit([])
            return
        
        from friday_ai.core.signals import signals
        signals.search_requested.emit(query)

        self.search_started.emit()
        self._worker = BackgroundWorker(
            self._do_search, self._project_root, query, case_sensitive,
        )
        self._worker.result_ready.connect(self._on_results)
        self._worker.start()

    def cancel(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.terminate()

    @staticmethod
    def _do_search(root: str, query: str, case_sensitive: bool) -> list[SearchMatch]:
        matches = []
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        max_results = 500

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                if len(matches) >= max_results:
                    return matches
                ext = Path(filename).suffix.lower()
                if ext not in _TEXT_EXTENSIONS:
                    continue
                filepath = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(filepath)
                    if size > _MAX_FILE_SIZE:
                        continue
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            for m in pattern.finditer(line):
                                matches.append(SearchMatch(
                                    file_path=filepath,
                                    line_number=line_num,
                                    line_content=line.rstrip(),
                                    match_start=m.start(),
                                    match_end=m.end(),
                                ))
                                if len(matches) >= max_results:
                                    return matches
                except (OSError, UnicodeDecodeError):
                    continue
        return matches

    def _on_results(self, result: object) -> None:
        if isinstance(result, list):
            self.results_ready.emit(result)
            self.search_finished.emit(len(result))
        else:
            self.results_ready.emit([])
            self.search_finished.emit(0)
