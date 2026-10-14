from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QObject

from friday_ai.core.signals import signals
from friday_ai.core.workers import BackgroundWorker
from shared.logger import get_logger

LOG = get_logger("friday.toolchain")


@dataclass
class ToolchainInfo:
    """A detected tool or runtime on the system."""
    name: str           # Human-readable, e.g. "Python 3.11.4"
    tool_type: str      # "python" | "node" | "java" | "gcc" | "gpp" | "clang" | "msvc" | "git" | "cmake" | "make" | "docker"
    path: str           # Absolute path to the executable
    version: str        # Version string, e.g. "3.11.4"


class ToolchainManager(QObject):
    """
    Service for discovering development tools and runtimes on the local machine.
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cache: list[ToolchainInfo] = []
        self._worker: Optional[BackgroundWorker] = None

    def detect_all(self) -> list[ToolchainInfo]:
        """
        Trigger an asynchronous scan for all known tool types.
        Caches results and emits signals.toolchains_updated upon completion.
        Returns the current (possibly empty) cache immediately.
        """
        LOG.info("Starting background detection of all toolchains...")
        self._worker = BackgroundWorker(self._perform_full_scan)
        self._worker.result_ready.connect(self._on_scan_complete)
        self._worker.start()
        return self._cache

    def get_all(self) -> list[ToolchainInfo]:
        """Return the currently cached toolchains."""
        return self._cache

    def get_by_type(self, tool_type: str) -> list[ToolchainInfo]:
        """Filter cached toolchains by a specific type."""
        return [t for t in self._cache if t.tool_type == tool_type]

    def detect_tool(self, tool_type: str) -> ToolchainInfo | None:
        """Synchronously detect a specific tool."""
        if tool_type == "python":
            pythons = self.detect_python_versions()
            return pythons[0] if pythons else None
        elif tool_type == "node":
            return self.detect_node()
        elif tool_type == "java":
            return self.detect_java()
        elif tool_type == "gcc":
            return self.detect_gcc()
        elif tool_type == "gpp":
            return self.detect_gpp()
        elif tool_type == "clang":
            return self._detect_generic("clang", ["clang"], r"clang version\s+([\d\.]+)")
        elif tool_type == "msvc":
            return self._detect_msvc()
        elif tool_type == "git":
            return self.detect_git()
        elif tool_type == "cmake":
            return self._detect_generic("cmake", ["cmake"], r"cmake version\s+([\d\.]+)")
        elif tool_type == "make":
            return self._detect_generic("make", ["make", "mingw32-make"], r"Make\s+([\d\.]+)")
        elif tool_type == "docker":
            return self._detect_generic("docker", ["docker"], r"Docker version\s+([\d\.]+)")
        
        LOG.warning(f"Unknown tool type requested for detection: {tool_type}")
        return None

    def detect_python_versions(self) -> list[ToolchainInfo]:
        """Detect all Python versions available on the system."""
        results = []
        seen_paths = set()

        # 1. Check standard python/python3 executables in PATH
        for cmd in ["python", "python3"]:
            info = self._detect_generic("python", [cmd], r"Python\s+([\d\.]+)")
            if info and info.path not in seen_paths:
                seen_paths.add(info.path)
                results.append(info)

        # 2. On Windows, use the 'py' launcher if available to find all installed versions
        if os.name == "nt":
            py_exe = shutil.which("py")
            if py_exe:
                try:
                    result = subprocess.run([py_exe, "-0p"], capture_output=True, text=True, check=False, creationflags=0x08000000)
                    for line in result.stdout.splitlines():
                        # Parse lines like: " -V:3.11 *        C:\Users\...\python.exe"
                        match = re.match(r"\s*-V:([\d\.]+)\s*\*?\s+(.*)", line)
                        if match:
                            version = match.group(1)
                            path = match.group(2).strip()
                            if path not in seen_paths and os.path.exists(path):
                                seen_paths.add(path)
                                results.append(ToolchainInfo(
                                    name=f"Python {version}",
                                    tool_type="python",
                                    path=path,
                                    version=version
                                ))
                except Exception as e:
                    LOG.debug(f"Error querying Windows py launcher: {e}")

        return results

    def detect_node(self) -> ToolchainInfo | None:
        return self._detect_generic("node", ["node"], r"v([\d\.]+)")

    def detect_java(self) -> ToolchainInfo | None:
        return self._detect_generic("java", ["java"], r"version\s+\"([^\"]+)\"", version_arg="-version", use_stderr=True)

    def detect_gcc(self) -> ToolchainInfo | None:
        return self._detect_generic("gcc", ["gcc"], r"([\d\.]+)")

    def detect_gpp(self) -> ToolchainInfo | None:
        return self._detect_generic("gpp", ["g++"], r"([\d\.]+)")

    def detect_git(self) -> ToolchainInfo | None:
        return self._detect_generic("git", ["git"], r"version\s+([\d\.]+)")

    # --- Private implementation details ---

    def _perform_full_scan(self) -> list[ToolchainInfo]:
        """Runs synchronously in a background thread to detect all tools."""
        tools = []
        
        # Python returns a list, others return a single ToolchainInfo or None
        tools.extend(self.detect_python_versions())
        
        for tool_type in ["node", "java", "gcc", "gpp", "clang", "msvc", "git", "cmake", "make", "docker"]:
            info = self.detect_tool(tool_type)
            if info:
                tools.append(info)
                
        return tools

    def _on_scan_complete(self, results: list[ToolchainInfo]) -> None:
        """Callback for when the background scan finishes."""
        self._cache = results
        LOG.info(f"Toolchain scan complete. Cached {len(self._cache)} toolchains.")
        signals.toolchains_updated.emit()

    def _detect_generic(self, 
                        tool_type: str, 
                        commands: list[str], 
                        version_regex: str, 
                        version_arg: str = "--version", 
                        use_stderr: bool = False) -> ToolchainInfo | None:
        """Helper to invoke a command and parse its version output."""
        for cmd in commands:
            executable = shutil.which(cmd)
            if executable:
                try:
                    result = subprocess.run(
                        [executable, version_arg],
                        capture_output=True,
                        text=True,
                        check=False,
                        creationflags=0x08000000
                    )
                    # Use stderr if explicitly requested, otherwise stdout (fallback to stderr if stdout is empty)
                    output = result.stderr if use_stderr else result.stdout
                    if not output and not use_stderr:
                        output = result.stderr

                    # Search only in the first line if possible to avoid spurious matches,
                    # but some tools output empty first lines, so search all output.
                    match = re.search(version_regex, output, re.IGNORECASE)
                    if match:
                        version = match.group(1)
                        name = f"{tool_type.capitalize()} {version}"
                        return ToolchainInfo(
                            name=name,
                            tool_type=tool_type,
                            path=executable,
                            version=version
                        )
                except Exception as e:
                    LOG.debug(f"Error checking {cmd} version via {executable}: {e}")
                    
        return None

    def _detect_msvc(self) -> ToolchainInfo | None:
        """Specific detection for MSVC (cl.exe)."""
        cl_exe = shutil.which("cl")
        if cl_exe:
            try:
                # cl.exe outputs version info to stderr when run without arguments
                result = subprocess.run([cl_exe], capture_output=True, text=True, check=False, creationflags=0x08000000)
                match = re.search(r"Compiler Version\s+([\d\.]+)", result.stderr, re.IGNORECASE)
                if match:
                    version = match.group(1)
                    return ToolchainInfo(
                        name=f"MSVC {version}",
                        tool_type="msvc",
                        path=cl_exe,
                        version=version
                    )
            except Exception as e:
                LOG.debug(f"Error checking msvc version: {e}")
                
        return None
