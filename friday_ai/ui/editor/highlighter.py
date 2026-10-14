"""Syntax highlighting for the FRIDAY code editor.

Provides ``QSyntaxHighlighter`` subclasses for Python, JSON, Markdown, and
generic text.  The highlighter is selected based on file extension.

All colours come from the FRIDAY theme system to ensure consistency.
"""

from __future__ import annotations

import re
from typing import ClassVar

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from friday_ai.core.theme import THEME

# ── Helpers ──────────────────────────────────────────────────────────────

def _fmt(
    color: str,
    *,
    bold: bool = False,
    italic: bool = False,
) -> QTextCharFormat:
    """Create a QTextCharFormat with the given colour and style."""
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


# ── Colour palette (GitHub-dark inspired) ────────────────────────────────
_KEYWORD   = _fmt("#ff7b72", bold=True)
_BUILTIN   = _fmt("#79c0ff")
_STRING    = _fmt("#a5d6ff")
_COMMENT   = _fmt("#8b949e", italic=True)
_NUMBER    = _fmt("#79c0ff")
_DECORATOR = _fmt("#d2a8ff")
_FUNCTION  = _fmt("#d2a8ff")
_CLASS     = _fmt("#ffa657", bold=True)
_SELF      = _fmt("#ff7b72", italic=True)
_OPERATOR  = _fmt("#ff7b72")
_BRACE     = _fmt("#e6edf3")

# JSON
_JSON_KEY   = _fmt("#7ee787")
_JSON_STR   = _fmt("#a5d6ff")
_JSON_NUM   = _fmt("#79c0ff")
_JSON_BOOL  = _fmt("#ff7b72", bold=True)
_JSON_NULL  = _fmt("#ff7b72", bold=True)

# Markdown
_MD_HEADING  = _fmt("#79c0ff", bold=True)
_MD_BOLD     = _fmt("#e6edf3", bold=True)
_MD_ITALIC   = _fmt("#e6edf3", italic=True)
_MD_CODE     = _fmt("#a5d6ff")
_MD_LINK     = _fmt("#58a6ff")
_MD_LIST     = _fmt("#ff7b72")


# ── Python highlighter ───────────────────────────────────────────────────

_PY_KEYWORDS = (
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
)

_PY_BUILTINS = (
    "abs", "all", "any", "bin", "bool", "bytes", "callable", "chr",
    "dict", "dir", "enumerate", "filter", "float", "format", "frozenset",
    "getattr", "hasattr", "hash", "hex", "id", "input", "int",
    "isinstance", "issubclass", "iter", "len", "list", "map", "max",
    "min", "next", "object", "oct", "open", "ord", "pow", "print",
    "property", "range", "repr", "reversed", "round", "set", "setattr",
    "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple",
    "type", "vars", "zip",
)


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighting for Python source code."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []
        self._build_rules()

    def _build_rules(self) -> None:
        # Keywords
        kw_pattern = r"\b(" + "|".join(_PY_KEYWORDS) + r")\b"
        self._rules.append((re.compile(kw_pattern), _KEYWORD))

        # Builtins
        bi_pattern = r"\b(" + "|".join(_PY_BUILTINS) + r")\b"
        self._rules.append((re.compile(bi_pattern), _BUILTIN))

        # self
        self._rules.append((re.compile(r"\bself\b"), _SELF))

        # Decorators
        self._rules.append((re.compile(r"@\w+"), _DECORATOR))

        # Function definitions
        self._rules.append((re.compile(r"\bdef\s+(\w+)"), _FUNCTION))

        # Class definitions
        self._rules.append((re.compile(r"\bclass\s+(\w+)"), _CLASS))

        # Numbers
        self._rules.append((re.compile(r"\b\d+\.?\d*([eE][+-]?\d+)?\b"), _NUMBER))

        # Operators
        self._rules.append((re.compile(r"[+\-*/%=<>!&|^~]"), _OPERATOR))

        # Strings (single-line)
        self._rules.append((re.compile(r'f?"[^"\\]*(\\.[^"\\]*)*"'), _STRING))
        self._rules.append((re.compile(r"f?'[^'\\]*(\\.[^'\\]*)*'"), _STRING))

        # Comments (must be last to override other matches)
        self._rules.append((re.compile(r"#[^\n]*"), _COMMENT))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)

        # Multi-line strings (triple-quotes)
        self._highlight_multiline(text, '"""', 1)
        self._highlight_multiline(text, "'''", 2)

    def _highlight_multiline(self, text: str, delimiter: str, state: int) -> None:
        if self.previousBlockState() == state:
            start = 0
            offset = 0
        else:
            start = text.find(delimiter)
            if start == -1:
                return
            offset = len(delimiter)

        while start >= 0:
            end = text.find(delimiter, start + offset)
            if end == -1:
                self.setCurrentBlockState(state)
                length = len(text) - start
            else:
                length = end - start + len(delimiter)
            self.setFormat(start, length, _STRING)
            start = text.find(delimiter, start + length)
            offset = len(delimiter)


# ── JSON highlighter ─────────────────────────────────────────────────────

class JsonHighlighter(QSyntaxHighlighter):
    """Syntax highlighting for JSON files."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = [
            (re.compile(r'"[^"]*"\s*(?=:)'), _JSON_KEY),
            (re.compile(r':\s*"[^"]*"'), _JSON_STR),
            (re.compile(r"\b\d+\.?\d*([eE][+-]?\d+)?\b"), _JSON_NUM),
            (re.compile(r"\b(true|false)\b"), _JSON_BOOL),
            (re.compile(r"\bnull\b"), _JSON_NULL),
        ]

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ── Markdown highlighter ─────────────────────────────────────────────────

class MarkdownHighlighter(QSyntaxHighlighter):
    """Syntax highlighting for Markdown files."""

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = [
            (re.compile(r"^#{1,6}\s.*$", re.MULTILINE), _MD_HEADING),
            (re.compile(r"\*\*[^*]+\*\*"), _MD_BOLD),
            (re.compile(r"(?<!\*)\*(?!\*)[^*]+\*(?!\*)"), _MD_ITALIC),
            (re.compile(r"`[^`]+`"), _MD_CODE),
            (re.compile(r"\[([^\]]+)\]\([^\)]+\)"), _MD_LINK),
            (re.compile(r"^[\s]*[-*+]\s", re.MULTILINE), _MD_LIST),
            (re.compile(r"^>\s.*$", re.MULTILINE), _COMMENT),
        ]

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ── Factory ──────────────────────────────────────────────────────────────

_HIGHLIGHTER_MAP: dict[str, type[QSyntaxHighlighter]] = {
    ".py": PythonHighlighter,
    ".pyw": PythonHighlighter,
    ".json": JsonHighlighter,
    ".md": MarkdownHighlighter,
    ".markdown": MarkdownHighlighter,
}


def get_highlighter(extension: str, document: QTextDocument) -> QSyntaxHighlighter | None:
    """Return an appropriate highlighter for the file extension, or None."""
    cls = _HIGHLIGHTER_MAP.get(extension.lower())
    if cls is not None:
        return cls(document)
    return None


def get_file_type(extension: str) -> str:
    """Return a human-readable file type label."""
    types = {
        ".py": "Python", ".pyw": "Python",
        ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "React JSX", ".tsx": "React TSX",
        ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
        ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
        ".toml": "TOML", ".ini": "INI",
        ".md": "Markdown", ".markdown": "Markdown",
        ".rst": "reStructuredText",
        ".txt": "Plain Text", ".csv": "CSV",
        ".java": "Java", ".kt": "Kotlin",
        ".c": "C", ".cpp": "C++", ".h": "C Header", ".hpp": "C++ Header",
        ".cs": "C#", ".go": "Go", ".rs": "Rust",
        ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
        ".sql": "SQL",
        ".sh": "Shell", ".bash": "Bash", ".ps1": "PowerShell",
        ".bat": "Batch", ".cmd": "Batch",
        ".xml": "XML", ".svg": "SVG",
        ".gitignore": "Git Ignore",
    }
    return types.get(extension.lower(), "Plain Text")


def get_line_ending(content: str) -> str:
    """Detect the line ending style from file content."""
    if "\r\n" in content:
        return "CRLF"
    elif "\r" in content:
        return "CR"
    return "LF"
