"""File indexing logic for the Project Brain.

Extracts symbols, classes, functions, and imports from files using AST parsing
where possible, and regex fallbacks for other languages.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re
from pathlib import Path

from friday_ai.brain.models import FileIndex, SymbolInfo
from friday_ai.ui.editor.highlighter import get_file_type
from shared.logger import get_logger

LOG = get_logger("friday.indexer")


class FileIndexer:
    """Parses files and extracts symbols."""

    @classmethod
    def index_file(cls, path: str | Path) -> FileIndex | None:
        """Parse a file and extract all symbols and imports."""
        path_obj = Path(path)
        if not path_obj.exists() or not path_obj.is_file():
            return None
        
        try:
            content = path_obj.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None  # Binary or unreadable

        # Compute hash to detect changes
        file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        ext = path_obj.suffix.lower()
        language = get_file_type(ext)
        
        file_idx = FileIndex(
            path=str(path_obj.resolve()),
            file_hash=file_hash,
            language=language,
            line_count=content.count('\n') + 1,
            size_bytes=len(content.encode("utf-8")),
        )

        if ext == ".py":
            cls._index_python(content, file_idx)
        else:
            cls._index_generic(content, file_idx)

        return file_idx

    @classmethod
    def _index_python(cls, content: str, file_idx: FileIndex) -> None:
        """Parse Python files using ast."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fall back to generic if AST fails due to invalid syntax
            cls._index_generic(content, file_idx)
            return

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                file_idx.symbols.append(SymbolInfo(
                    name=node.name,
                    kind="class",
                    line=node.lineno,
                    file_path=file_idx.path,
                    docstring=docstring,
                ))
                # Methods
                for subnode in node.body:
                    if isinstance(subnode, ast.FunctionDef) or isinstance(subnode, ast.AsyncFunctionDef):
                        sub_doc = ast.get_docstring(subnode) or ""
                        # Try to build signature
                        sig = cls._build_py_signature(subnode)
                        file_idx.symbols.append(SymbolInfo(
                            name=f"{node.name}.{subnode.name}",
                            kind="method",
                            line=subnode.lineno,
                            file_path=file_idx.path,
                            signature=sig,
                            docstring=sub_doc,
                        ))

            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                docstring = ast.get_docstring(node) or ""
                sig = cls._build_py_signature(node)
                file_idx.symbols.append(SymbolInfo(
                    name=node.name,
                    kind="function",
                    line=node.lineno,
                    file_path=file_idx.path,
                    signature=sig,
                    docstring=docstring,
                ))
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    file_idx.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    file_idx.imports.append(node.module)

    @classmethod
    def _build_py_signature(cls, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Roughly reconstruct the function signature."""
        args = []
        for a in node.args.args:
            args.append(a.arg)
        # simplified representation
        return f"{node.name}({', '.join(args)})"

    @classmethod
    def _index_generic(cls, content: str, file_idx: FileIndex) -> None:
        """Regex fallback for other languages (JS/TS, C++, Java, etc)."""
        # Generic function detection: function name(...) or class Name {
        # This is a very rough heuristic
        lines = content.splitlines()
        
        class_pattern = re.compile(r'^\s*(?:export\s+)?(?:public\s+|private\s+)?class\s+([A-Za-z0-9_]+)', re.IGNORECASE)
        func_pattern = re.compile(r'^\s*(?:export\s+)?(?:public\s+|private\s+)?(?:static\s+)?(?:async\s+)?(?:function\s+)?([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:{|:)', re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            class_match = class_pattern.search(line)
            if class_match:
                file_idx.symbols.append(SymbolInfo(
                    name=class_match.group(1),
                    kind="class",
                    line=i,
                    file_path=file_idx.path,
                ))
                continue
                
            func_match = func_pattern.search(line)
            if func_match:
                # Exclude common control flow keywords
                name = func_match.group(1)
                if name not in ("if", "for", "while", "switch", "catch"):
                    file_idx.symbols.append(SymbolInfo(
                        name=name,
                        kind="function",
                        line=i,
                        file_path=file_idx.path,
                    ))
