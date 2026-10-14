"""Interpreter Manager — detects and manages language runtimes."""

import shutil
import platform
from typing import Optional

class InterpreterManager:
    """Discovers installed programming language interpreters."""
    
    def __init__(self):
        self._python_path: Optional[str] = None
        self._detect_python()

    def _detect_python(self) -> None:
        """Finds the best available Python interpreter."""
        # Detect in order of preference
        candidates = ["python", "py", "python3"]
        if platform.system() == "Linux":
            candidates = ["python3", "python"]
            
        for candidate in candidates:
            path = shutil.which(candidate)
            if path:
                self._python_path = path
                break

    def get_python_path(self) -> Optional[str]:
        """Returns the absolute path to the Python executable, or None if missing."""
        return self._python_path

    def has_python(self) -> bool:
        return self._python_path is not None
