"""Project Brain — The continuously updated project knowledge engine.

Maintains a full workspace index of symbols, imports, and metadata.
Automatically updates incrementally when files change.
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QObject, QFileSystemWatcher, pyqtSignal as Signal

from friday_ai.brain.models import WorkspaceIndex, SymbolInfo, FileIndex
from friday_ai.brain.indexer import FileIndexer
from friday_ai.core.signals import signals
from friday_ai.core.workers import BackgroundWorker
from shared.logger import get_logger

LOG = get_logger("friday.brain")

_SKIP_DIRS = frozenset({
    ".git", ".svn", "__pycache__", "node_modules", ".venv",
    "venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".idea", ".vs",
})

_TEXT_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".md", ".rst", ".txt", ".csv",
    ".java", ".kt", ".c", ".cpp", ".h", ".hpp", ".cs",
    ".go", ".rs", ".rb", ".php", ".swift", ".sql",
    ".sh", ".bash", ".ps1", ".bat", ".cmd",
    ".xml", ".env",
})

_MAX_FILE_SIZE = 1_000_000  # 1 MB


class ProjectBrain(QObject):
    """Knowledge engine for the current project."""
    
    index_updated = Signal()  # Emitted when the index finishes a background update

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.index: WorkspaceIndex | None = None
        self._watcher = QFileSystemWatcher(self)
        self._worker: BackgroundWorker | None = None
        
        self._watcher.fileChanged.connect(self._on_file_changed)
        
        # Wire to core signals
        signals.project_opened.connect(self._on_project_opened)
        signals.project_closed.connect(self._on_project_closed)
        signals.file_saved.connect(self._on_file_saved)

    # ── Lifecycle ────────────────────────────────────────────────────────
    
    def _on_project_opened(self, path: str) -> None:
        LOG.info("ProjectBrain: Initializing for %s", path)
        self.index = WorkspaceIndex(project_root=path)
        self._start_full_scan(path)
        
    def _on_project_closed(self) -> None:
        LOG.info("ProjectBrain: Clearing index")
        self.index = None
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker = None
        # Clear watcher
        files = self._watcher.files()
        if files:
            self._watcher.removePaths(files)
            
    def _on_file_saved(self, path: str) -> None:
        """Triggered by the IDE when a file is saved."""
        self._on_file_changed(path)
            
    def _on_file_changed(self, path: str) -> None:
        """Triggered by QFileSystemWatcher or IDE save."""
        if not self.index:
            return
        
        # Offload single file re-index to background
        self._worker = BackgroundWorker(self._index_single_file, path)
        self._worker.result_ready.connect(self._on_single_file_indexed)
        self._worker.start()

    # ── Background Scanning ─────────────────────────────────────────────

    def _start_full_scan(self, path: str) -> None:
        signals.mission_update.emit("INDEX", "Building Project Brain...")
        self._worker = BackgroundWorker(self._scan_project, path)
        self._worker.result_ready.connect(self._on_full_scan_complete)
        self._worker.start()

    @staticmethod
    def _scan_project(root: str) -> tuple[dict[str, FileIndex], list[str]]:
        """Scan all valid files in the project. Returns (files, paths_to_watch)."""
        files: dict[str, FileIndex] = {}
        paths_to_watch: list[str] = []
        
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                if ext not in _TEXT_EXTENSIONS:
                    continue
                
                filepath = os.path.join(dirpath, filename)
                try:
                    if os.path.getsize(filepath) > _MAX_FILE_SIZE:
                        continue
                    
                    file_idx = FileIndexer.index_file(filepath)
                    if file_idx:
                        files[filepath] = file_idx
                        paths_to_watch.append(filepath)
                except OSError:
                    continue
                    
        return files, paths_to_watch

    def _on_full_scan_complete(self, result: object) -> None:
        if isinstance(result, tuple) and len(result) == 2 and self.index:
            files_dict, watch_paths = result
            self.index.files = files_dict
            
            # Watch these files for changes outside the IDE
            if watch_paths:
                # QFileSystemWatcher has a limit on some OSes, but we'll try to add them
                chunk_size = 500
                for i in range(0, len(watch_paths), chunk_size):
                    self._watcher.addPaths(watch_paths[i:i+chunk_size])
                    
            signals.mission_update.emit("READY", f"Brain indexed {len(files_dict)} files")
            LOG.info("ProjectBrain scan complete: %d files indexed", len(files_dict))
            self.index_updated.emit()
            
    @staticmethod
    def _index_single_file(path: str) -> FileIndex | None:
        try:
            if os.path.getsize(path) > _MAX_FILE_SIZE:
                return None
            return FileIndexer.index_file(path)
        except OSError:
            return None

    def _on_single_file_indexed(self, result: object) -> None:
        if isinstance(result, FileIndex) and self.index:
            # Check hash to see if we actually need to update
            old_idx = self.index.files.get(result.path)
            if old_idx and old_idx.file_hash == result.file_hash:
                return # No semantic change
                
            self.index.files[result.path] = result
            LOG.debug("ProjectBrain: Re-indexed %s", result.path)
            self.index_updated.emit()

    # ── Public AI API ───────────────────────────────────────────────────

    def get_file_symbols(self, path: str) -> list[SymbolInfo]:
        if not self.index:
            return []
        norm_path = str(Path(path).resolve())
        f = self.index.files.get(norm_path)
        return f.symbols if f else []

    def search_symbols(self, query: str) -> list[SymbolInfo]:
        if not self.index:
            return []
        return self.index.search_symbols(query)

    def find_definition(self, name: str) -> list[SymbolInfo]:
        if not self.index:
            return []
        return self.index.get_symbol(name)

    def find_related_symbols(self, current_file: str) -> list[SymbolInfo]:
        """Find symbols that are imported or related to the current file."""
        if not self.index:
            return []
        norm_path = str(Path(current_file).resolve())
        f = self.index.files.get(norm_path)
        if not f:
            return []
            
        related = []
        for imp in f.imports:
            # Very basic resolution: if import matches a symbol name
            # e.g. from x import y -> y is the symbol
            matches = self.index.get_symbol(imp)
            related.extend(matches)
        return related

    def find_similar_files(self, path: str) -> list[str]:
        """Find files in the same directory or with same extension."""
        if not self.index:
            return []
        norm_path = str(Path(path).resolve())
        parent = str(Path(norm_path).parent)
        
        similar = []
        for fpath in self.index.files.keys():
            if fpath != norm_path and fpath.startswith(parent):
                similar.append(fpath)
        return similar
