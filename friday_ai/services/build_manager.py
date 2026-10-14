from __future__ import annotations

import re
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from PyQt5.QtCore import QObject, QProcess

from friday_ai.core.signals import signals
from friday_ai.services.toolchain_manager import ToolchainManager
from shared.logger import get_logger

LOG = get_logger("friday.build")

@dataclass
class BuildResult:
    """Result of a build operation."""
    success: bool
    exit_code: int
    output: str
    errors: list = field(default_factory=list)   # list of problem dicts
    elapsed: float = 0.0
    output_path: str | None = None               # Path to compiled binary


class BuildStrategy(ABC):
    """Base class for build strategies. Extensible for Make, CMake, Maven, etc."""
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        ...

    @abstractmethod
    def can_build(self, project_path: Path, file_path: Path) -> bool:
        ...

    @abstractmethod
    def get_build_command(self, file_path: Path, cwd: Path) -> tuple[str, list[str], str]:
        """Returns (program, args, output_path)."""
        ...

    def parse_errors(self, output: str) -> list[dict]:
        """Parse build output for errors and warnings."""
        return []


class GccBuildStrategy(BuildStrategy):
    def __init__(self, toolchain: ToolchainManager):
        self.toolchain = toolchain

    @property
    def name(self) -> str:
        return "gcc"

    @property
    def supported_extensions(self) -> list[str]:
        return [".c"]

    def can_build(self, project_path: Path, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    def get_build_command(self, file_path: Path, cwd: Path) -> tuple[str, list[str], str]:
        gcc_path = self.toolchain.get_tool_path("gcc") or "gcc"
        output_stem = file_path.stem
        if sys.platform == "win32":
            output_stem += ".exe"
        output_path = cwd / output_stem
        args = [str(file_path), "-o", str(output_path)]
        return str(gcc_path), args, str(output_path)

    def parse_errors(self, output: str) -> list[dict]:
        errors = []
        pattern = re.compile(r"^(.+\.[ch]):(\d+):(?:\d+:)?\s+(error|warning):\s+(.+)", re.MULTILINE)
        for match in pattern.finditer(output):
            errors.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'severity': match.group(3),
                'message': match.group(4)
            })
        return errors


class GppBuildStrategy(BuildStrategy):
    def __init__(self, toolchain: ToolchainManager):
        self.toolchain = toolchain

    @property
    def name(self) -> str:
        return "g++"

    @property
    def supported_extensions(self) -> list[str]:
        return [".cpp", ".cc", ".cxx", ".hpp", ".h"]

    def can_build(self, project_path: Path, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    def get_build_command(self, file_path: Path, cwd: Path) -> tuple[str, list[str], str]:
        gpp_path = self.toolchain.get_tool_path("g++") or "g++"
        output_stem = file_path.stem
        if sys.platform == "win32":
            output_stem += ".exe"
        output_path = cwd / output_stem
        args = [str(file_path), "-o", str(output_path)]
        return str(gpp_path), args, str(output_path)

    def parse_errors(self, output: str) -> list[dict]:
        errors = []
        pattern = re.compile(r"^(.+\.[ch](?:pp|xx)?):(\d+):(?:\d+:)?\s+(error|warning):\s+(.+)", re.MULTILINE)
        for match in pattern.finditer(output):
            errors.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'severity': match.group(3),
                'message': match.group(4)
            })
        return errors


class JavacBuildStrategy(BuildStrategy):
    def __init__(self, toolchain: ToolchainManager):
        self.toolchain = toolchain

    @property
    def name(self) -> str:
        return "javac"

    @property
    def supported_extensions(self) -> list[str]:
        return [".java"]

    def can_build(self, project_path: Path, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    def get_build_command(self, file_path: Path, cwd: Path) -> tuple[str, list[str], str]:
        javac_path = self.toolchain.get_tool_path("javac") or "javac"
        output_path = cwd / (file_path.stem + ".class")
        args = [str(file_path)]
        return str(javac_path), args, str(output_path)

    def parse_errors(self, output: str) -> list[dict]:
        errors = []
        pattern = re.compile(r"^(.+\.java):(\d+):\s+(error|warning):\s+(.+)", re.MULTILINE)
        for match in pattern.finditer(output):
            errors.append({
                'file': match.group(1),
                'line': int(match.group(2)),
                'severity': match.group(3),
                'message': match.group(4)
            })
        return errors


class BuildManager(QObject):
    def __init__(self, toolchain: ToolchainManager, parent: QObject | None = None):
        super().__init__(parent)
        self.toolchain = toolchain
        self.strategies: list[BuildStrategy] = []
        self._process: QProcess | None = None
        self._current_file: str = ""
        self._current_strategy: BuildStrategy | None = None
        self._start_time: float = 0.0
        self._output_buffer: list[str] = []
        self._current_output_path: str | None = None

        # Register default strategies
        self.register_strategy(GccBuildStrategy(self.toolchain))
        self.register_strategy(GppBuildStrategy(self.toolchain))
        self.register_strategy(JavacBuildStrategy(self.toolchain))

    def register_strategy(self, strategy: BuildStrategy) -> None:
        self.strategies.append(strategy)
        LOG.debug(f"Registered build strategy: {strategy.name}")

    def can_build(self, file_path: str) -> bool:
        path = Path(file_path)
        for strategy in self.strategies:
            if path.suffix.lower() in strategy.supported_extensions:
                return True
        return False

    def is_building(self) -> bool:
        return self._process is not None and self._process.state() == QProcess.ProcessState.Running

    def cancel_build(self) -> None:
        if self.is_building():
            LOG.info("Canceling build process")
            self._process.kill()
            self._process.waitForFinished(1000)

    def build_file(self, file_path: str, cwd: str = "") -> None:
        if self.is_building():
            LOG.warning("A build is already in progress.")
            return

        path = Path(file_path)
        project_cwd = Path(cwd) if cwd else path.parent

        strategy = None
        for strat in self.strategies:
            if strat.can_build(project_cwd, path):
                strategy = strat
                break

        if not strategy:
            LOG.error(f"No build strategy found for {file_path}")
            return

        program, args, output_path = strategy.get_build_command(path, project_cwd)
        self._current_file = file_path
        self._current_strategy = strategy
        self._current_output_path = output_path
        self._start_time = time.time()
        self._output_buffer = []

        self._process = QProcess(self)
        self._process.setWorkingDirectory(str(project_cwd))

        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error_occurred)

        LOG.info(f"Starting build: {program} {' '.join(args)}")
        signals.build_started.emit(self._current_file)

        self._process.start(program, args)

    def _on_stdout(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self._output_buffer.append(data)
        signals.build_output.emit(data, 'build')

    def _on_stderr(self) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        self._output_buffer.append(data)
        signals.build_output.emit(data, 'build')

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        elapsed = time.time() - self._start_time
        success = exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        
        full_output = "".join(self._output_buffer)
        errors = []
        if self._current_strategy:
            errors = self._current_strategy.parse_errors(full_output)
            
        result = BuildResult(
            success=success,
            exit_code=exit_code,
            output=full_output,
            errors=errors,
            elapsed=elapsed,
            output_path=self._current_output_path
        )
        
        LOG.info(f"Build finished for {self._current_file} with exit code {exit_code}")
        signals.build_finished.emit(self._current_file, exit_code)
        
        self._cleanup()

    def _on_error_occurred(self, error: QProcess.ProcessError) -> None:
        LOG.error(f"Build process error occurred: {error}")
        if self._process:
            error_msg = self._process.errorString()
            signals.build_output.emit(f"Process Error: {error_msg}\n", 'build')
            self._output_buffer.append(f"Process Error: {error_msg}\n")

    def _cleanup(self) -> None:
        if self._process:
            self._process.deleteLater()
            self._process = None
        self._current_file = ""
        self._current_strategy = None
        self._current_output_path = None
        self._output_buffer = []
