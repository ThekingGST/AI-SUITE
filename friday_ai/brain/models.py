"""Data models for the Project Brain."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SymbolInfo:
    """A symbol extracted from a file."""
    name: str
    kind: str  # "class", "function", "method", "variable"
    line: int
    file_path: str
    signature: str = ""
    docstring: str = ""


@dataclass
class FileIndex:
    """The indexed contents of a single file."""
    path: str
    file_hash: str
    language: str
    symbols: list[SymbolInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    line_count: int = 0
    size_bytes: int = 0


@dataclass
class WorkspaceIndex:
    """The complete index of the workspace."""
    project_root: str
    files: dict[str, FileIndex] = field(default_factory=dict)
    
    def get_symbol(self, name: str) -> list[SymbolInfo]:
        """Find all symbols matching a given name."""
        results = []
        for f in self.files.values():
            for s in f.symbols:
                if s.name == name:
                    results.append(s)
        return results

    def search_symbols(self, query: str) -> list[SymbolInfo]:
        """Search symbols containing the query."""
        results = []
        q = query.lower()
        for f in self.files.values():
            for s in f.symbols:
                if q in s.name.lower():
                    results.append(s)
        return results
