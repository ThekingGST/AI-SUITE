"""Diagnostics Service — parses stderr to detect common runtime errors."""

import re
from typing import Optional

class DiagnosticsService:
    """Analyzes execution output to provide readable error diagnostics."""

    # Common Python error patterns
    _PYTHON_ERROR_REGEX = re.compile(r"([A-Za-z]+Error):\s*(.*)")
    
    def __init__(self):
        self._last_error_type: Optional[str] = None
        self._last_error_msg: Optional[str] = None
        self._raw_stderr: str = ""

    def reset(self) -> None:
        self._last_error_type = None
        self._last_error_msg = None
        self._raw_stderr = ""

    def analyze_stderr_chunk(self, chunk: str) -> None:
        """Process a chunk of stderr to find errors."""
        self._raw_stderr += chunk
        
        # Scan for the last exception type
        for match in self._PYTHON_ERROR_REGEX.finditer(chunk):
            self._last_error_type = match.group(1)
            self._last_error_msg = match.group(2)

    def get_friendly_diagnostic(self) -> Optional[str]:
        """Convert the last seen error into a friendly diagnostic."""
        if not self._last_error_type:
            return None

        # Custom friendly mappings
        if self._last_error_type == "ModuleNotFoundError":
            module_name = self._last_error_msg.replace("No module named ", "").strip("'")
            return f"{module_name.title()} isn't installed.\n\nRun:\npip install {module_name}"
            
        if self._last_error_type == "FileNotFoundError":
            return f"The file could not be found: {self._last_error_msg}"
            
        if self._last_error_type == "SyntaxError":
            return f"There is a syntax error in your code: {self._last_error_msg}"

        return f"{self._last_error_type}: {self._last_error_msg}"

    def get_raw_stderr(self) -> str:
        return self._raw_stderr

    def has_error(self) -> bool:
        return self._last_error_type is not None
