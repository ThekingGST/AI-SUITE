from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from utils.constants import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
)
from utils.helpers import iter_user_search_roots, safe_open_path
from utils.logger import LOGGER


@dataclass
class FileMatch:
    path: Path
    score: int
    modified: float


class FileAssistant:
    def __init__(self) -> None:
        self.roots = list(iter_user_search_roots())
        self._index: list[Path] = []
        self._indexed_at = 0.0

    def refresh_index(self) -> int:
        files: list[Path] = []
        for root in self.roots:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                for filename in filenames:
                    files.append(Path(dirpath) / filename)
        self._index = files
        self._indexed_at = time.time()
        LOGGER.info("Indexed %d user files.", len(files))
        return len(files)

    def search(self, query: str, limit: int = 10) -> list[Path]:
        if not self._index or time.time() - self._indexed_at > 900:
            self.refresh_index()
        terms = [term for term in query.lower().split() if term]
        matches: list[FileMatch] = []
        for path in self._index:
            name = path.stem.lower()
            suffix = path.suffix.lower()
            score = sum(3 for term in terms if term in name)
            if any(term in str(path.parent).lower() for term in terms):
                score += 1
            if "image" in terms and suffix in SUPPORTED_IMAGE_EXTENSIONS:
                score += 2
            if "video" in terms and suffix in SUPPORTED_VIDEO_EXTENSIONS:
                score += 2
            if ("notes" in terms or "pdf" in terms) and suffix in SUPPORTED_DOCUMENT_EXTENSIONS:
                score += 2
            if score:
                try:
                    modified = path.stat().st_mtime
                except OSError:
                    modified = 0
                matches.append(FileMatch(path, score, modified))
        matches.sort(key=lambda m: (m.score, m.modified), reverse=True)
        return [m.path for m in matches[:limit]]

    def open_best(self, query: str) -> str:
        matches = self.search(query, limit=1)
        if not matches:
            return f"I could not find a file matching {query}."
        return "Opened " + str(matches[0]) if safe_open_path(matches[0]) else "I found it, but could not open it."

    def latest_screenshot(self) -> Path | None:
        candidates: list[Path] = []
        for root in self.roots:
            shot_dir = root
            if shot_dir.exists():
                candidates.extend(
                    p for p in shot_dir.glob("*screenshot*") if p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
                )
        return max(candidates, key=lambda p: p.stat().st_mtime, default=None)

    def delete_temp_files(self) -> str:
        temp = Path(os.environ.get("TEMP", ""))
        if not temp.exists() or len(str(temp)) < 5:
            return "Temporary folder was not found."
        removed = 0
        for item in temp.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    removed += 1
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    removed += 1
            except OSError:
                continue
        return f"Removed {removed} temporary items."
