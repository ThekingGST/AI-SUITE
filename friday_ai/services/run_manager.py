"""Run manager — executes files through language-specific runners.

Architecture:
    RunManager → BuildManager → BuildStrategy
    RunManager → LanguageRunnerFactory → Language Runners
    RunManager → EnvironmentManager → ToolchainManager

This module also exports the canonical ExecutionEvent dataclass,
which is emitted after every run completes. Downstream consumers
(AI, diagnostics, memory, analytics) subscribe to execution_completed
without modifying RunManager.
"""
from __future__ import annotations
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from PyQt5.QtCore import QObject, QProcess, pyqtSignal as Signal

from friday_ai.core.signals import signals
from shared.logger import get_logger
from friday_ai.ui.panels.problems_panel import Problem

LOG = get_logger("friday.run")


# ---------------------------------------------------------------------------
# ExecutionEvent — canonical execution record for the IDE
# ---------------------------------------------------------------------------

@dataclass
class ExecutionEvent:
    """Emitted after every run completes.

    This is the canonical execution record consumed by AI, diagnostics,
    memory, analytics, and the Project Brain. Future systems should
    subscribe to ``signals.execution_completed`` rather than parsing logs.
    """

    operation: str                        # "run" | "build" | "debug"
    file_path: str
    project_path: str | None = None
    working_directory: str = ""
    language: str = ""
    runtime: str = ""
    environment: str | None = None
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    elapsed: float = 0.0
    timestamp: str = ""
    diagnostics: list = field(default_factory=list)
    build_result: object | None = None    # BuildResult when applicable


class LanguageRunner(QObject):
    """Base class for language-specific runners."""
    output = Signal(str, str)  # (text, category)
    finished = Signal(int)     # (exit_code)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process: QProcess | None = None
        self._start_time = 0.0
        self._check_compiler()

    def _check_compiler(self) -> None:
        pass

    def run(self, file_path: str, cwd: str = "") -> None:
        raise NotImplementedError

    def stop(self) -> None:
        if self._process and self._process.state() == QProcess.ProcessState.Running:
            self._process.kill()
            LOG.info("Process killed")

    def is_running(self) -> bool:
        return self._process is not None and self._process.state() == QProcess.ProcessState.Running

    def _on_output(self, is_error: bool = False) -> None:
        if not self._process:
            return
        data = self._process.readAllStandardError() if is_error else self._process.readAllStandardOutput()
        if data:
            text = data.data().decode("utf-8", errors="replace")
            self.output.emit(text, self.category)

    def _start_process(self, program: str, args: list[str], cwd: str) -> None:
        self.stop()
        self._process = QProcess(self)
        self._process.setWorkingDirectory(cwd)
        self._process.readyReadStandardOutput.connect(lambda: self._on_output(False))
        self._process.readyReadStandardError.connect(lambda: self._on_output(True))
        self._process.finished.connect(self._on_finished)
        self._start_time = time.time()
        self._process.start(program, args)
        LOG.info("Running: %s %s", program, " ".join(args))

    def _on_finished(self, exit_code: int, status) -> None:
        elapsed = time.time() - self._start_time
        if exit_code == 0:
            self.output.emit(f"\n[Run Success] Elapsed: {elapsed:.2f}s\n", "build")
        else:
            self.output.emit(f"\n[Run Failed] Exit code: {exit_code} Elapsed: {elapsed:.2f}s\n", "build")
        self.finished.emit(exit_code)

    @property
    def category(self) -> str:
        return "system"

    @property
    def interpreter(self) -> str:
        return ""


class PythonRunner(LanguageRunner):
    @property
    def category(self) -> str: return "python"

    def _check_compiler(self) -> None:
        self._interpreter = self._detect_interpreter()
        if not self._interpreter:
            signals.mission_update.emit("ERROR", "Python interpreter not found.")
            self.output.emit("[Error] Python interpreter not found.\n", "build")

    @staticmethod
    def _detect_interpreter() -> str:
        venv_python = Path(sys.prefix) / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        return shutil.which("python") or shutil.which("python3") or sys.executable

    @property
    def interpreter(self) -> str:
        return self._interpreter

    def run(self, file_path: str, cwd: str = "") -> None:
        if not self._interpreter:
            self._check_compiler()
            if not self._interpreter:
                self.finished.emit(1)
                return
        self._start_process(self._interpreter, ["-u", file_path], cwd or str(Path(file_path).parent))


class NodeRunner(LanguageRunner):
    @property
    def category(self) -> str: return "node"

    def _check_compiler(self) -> None:
        self._node = shutil.which("node")
        if not self._node:
            signals.mission_update.emit("ERROR", "Node.js not found.")
            self.output.emit("[Error] Node.js not found.\n", "build")

    @property
    def interpreter(self) -> str:
        return self._node or "node"

    def run(self, file_path: str, cwd: str = "") -> None:
        if not self._node:
            self._check_compiler()
            if not self._node:
                self.finished.emit(1)
                return
        self._start_process(self._node, [file_path], cwd or str(Path(file_path).parent))


class CompiledRunner(LanguageRunner):
    """Base for C, C++, Java."""
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._compile_process: QProcess | None = None
        self._run_file = ""
        self._run_cwd = ""
        self._compile_output = ""

    def stop(self) -> None:
        super().stop()
        if self._compile_process and self._compile_process.state() == QProcess.ProcessState.Running:
            self._compile_process.kill()

    def is_running(self) -> bool:
        c_running = self._compile_process is not None and self._compile_process.state() == QProcess.ProcessState.Running
        return super().is_running() or c_running

    def run(self, file_path: str, cwd: str = "") -> None:
        if not self._check_tools():
            self.finished.emit(1)
            return
        
        self.stop()
        self._run_file = file_path
        self._run_cwd = cwd or str(Path(file_path).parent)
        self._compile_output = ""
        
        signals.run_compile_started.emit(file_path)
        self.output.emit(f"Compiling {Path(file_path).name}...\n", "build")
        
        self._compile_process = QProcess(self)
        self._compile_process.setWorkingDirectory(self._run_cwd)
        self._compile_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._compile_process.readyReadStandardOutput.connect(self._on_compile_output)
        self._compile_process.finished.connect(self._on_compile_finished)
        
        cmd, args = self._get_compile_cmd(file_path)
        self._start_time = time.time()
        self._compile_process.start(cmd, args)

    def _on_compile_output(self) -> None:
        if not self._compile_process: return
        data = self._compile_process.readAllStandardOutput().data()
        text = data.decode("utf-8", errors="replace")
        self._compile_output += text
        self.output.emit(text, "build")

    def _on_compile_finished(self, exit_code: int, status) -> None:
        self._parse_errors(self._compile_output)
        signals.run_compile_finished.emit(self._run_file, exit_code)
        
        elapsed = time.time() - self._start_time
        if exit_code != 0:
            self.output.emit(f"\n[Compilation Failed] Exit code {exit_code} in {elapsed:.2f}s\n", "build")
            self.finished.emit(exit_code)
            return
            
        self.output.emit(f"\n[Compilation Succeeded] Elapsed: {elapsed:.2f}s. Running...\n", "build")
        cmd, args = self._get_run_cmd(self._run_file)
        self._start_process(cmd, args, self._run_cwd)

    def _check_tools(self) -> bool:
        return False
    def _get_compile_cmd(self, file_path: str) -> tuple[str, list[str]]:
        return "", []
    def _get_run_cmd(self, file_path: str) -> tuple[str, list[str]]:
        return "", []
    def _parse_errors(self, output: str) -> None:
        pass


class JavaRunner(CompiledRunner):
    @property
    def category(self) -> str: return "java"

    def _check_tools(self) -> bool:
        self._javac = shutil.which("javac")
        self._java = shutil.which("java")
        if not self._javac or not self._java:
            signals.mission_update.emit("ERROR", "Java JDK not found.")
            self.output.emit("[Error] javac or java not found.\n", "build")
            return False
        return True

    @property
    def interpreter(self) -> str:
        return getattr(self, "_java", "java")

    def _get_compile_cmd(self, file_path: str) -> tuple[str, list[str]]:
        return self._javac, [Path(file_path).name]

    def _get_run_cmd(self, file_path: str) -> tuple[str, list[str]]:
        return self._java, [Path(file_path).stem]

    def _parse_errors(self, output: str) -> None:
        problems = []
        for line in output.splitlines():
            # e.g. Main.java:2: error: ...
            m = re.match(r"^(.+\.java):(\d+):\s+(error|warning):\s+(.+)", line.strip())
            if m:
                fname, lnum, sev, msg = m.groups()
                p = Problem(sev, msg, str(Path(self._run_cwd) / fname), int(lnum))
                problems.append(p)
        if problems:
            signals.problems_updated.emit(problems)


class CRunner(CompiledRunner):
    @property
    def category(self) -> str: return "c/c++"

    def _check_tools(self) -> bool:
        self._gcc = shutil.which("gcc")
        if not self._gcc:
            signals.mission_update.emit("ERROR", "GCC not found.")
            self.output.emit("[Error] gcc not found.\n", "build")
            return False
        return True

    @property
    def interpreter(self) -> str:
        return getattr(self, "_gcc", "gcc")

    def _get_compile_cmd(self, file_path: str) -> tuple[str, list[str]]:
        out = Path(file_path).stem
        if sys.platform == "win32":
            out += ".exe"
        return self._gcc, [Path(file_path).name, "-o", out]

    def _get_run_cmd(self, file_path: str) -> tuple[str, list[str]]:
        out = Path(file_path).stem
        if sys.platform == "win32":
            out += ".exe"
        return str(Path(self._run_cwd) / out), []

    def _parse_errors(self, output: str) -> None:
        problems = []
        for line in output.splitlines():
            # e.g. main.c:3:1: error: ...
            m = re.match(r"^(.+\.[ch]):(\d+):(?:\d+:)?\s+(error|warning):\s+(.+)", line.strip())
            if m:
                fname, lnum, sev, msg = m.groups()
                p = Problem(sev, msg, str(Path(self._run_cwd) / fname), int(lnum))
                problems.append(p)
        if problems:
            signals.problems_updated.emit(problems)


class CppRunner(CRunner):
    def _check_tools(self) -> bool:
        self._gpp = shutil.which("g++")
        if not self._gpp:
            signals.mission_update.emit("ERROR", "G++ not found.")
            self.output.emit("[Error] g++ not found.\n", "build")
            return False
        return True

    @property
    def interpreter(self) -> str:
        return getattr(self, "_gpp", "g++")

    def _get_compile_cmd(self, file_path: str) -> tuple[str, list[str]]:
        out = Path(file_path).stem
        if sys.platform == "win32":
            out += ".exe"
        return self._gpp, [Path(file_path).name, "-o", out]

    def _parse_errors(self, output: str) -> None:
        problems = []
        for line in output.splitlines():
            m = re.match(r"^(.+\.(?:cpp|hpp|h|cc)):(\d+):(?:\d+:)?\s+(error|warning):\s+(.+)", line.strip())
            if m:
                fname, lnum, sev, msg = m.groups()
                p = Problem(sev, msg, str(Path(self._run_cwd) / fname), int(lnum))
                problems.append(p)
        if problems:
            signals.problems_updated.emit(problems)


class LanguageRunnerFactory:
    """Creates appropriate runners for files."""
    _REGISTRY: dict[str, type[LanguageRunner]] = {
        ".py": PythonRunner,
        ".pyw": PythonRunner,
        ".js": NodeRunner,
        ".java": JavaRunner,
        ".c": CRunner,
        ".cpp": CppRunner,
        ".cc": CppRunner,
    }
    
    @classmethod
    def get_runner(cls, ext: str, parent: QObject | None = None) -> LanguageRunner | None:
        runner_cls = cls._REGISTRY.get(ext.lower())
        if runner_cls:
            return runner_cls(parent)
        return None


class RunManager(QObject):
    """Manages file execution through language-specific runners.

    This is the primary execution engine of FRIDAY.  It orchestrates:
      1. Project type detection (via ProjectManager)
      2. Environment resolution (via EnvironmentManager)
      3. Runtime selection (via ToolchainManager, through EnvironmentManager)
      4. Build if required (via BuildManager)
      5. Execution (via LanguageRunner)
      6. Output capture → Output Panel
      7. Diagnostics → Problems Panel
      8. ExecutionEvent → Signal Bus (for AI, Brain, Memory)
    """

    output = Signal(str, str)
    run_started = Signal(str)           # file path
    run_finished = Signal(str, int)     # file path, exit code

    def __init__(
        self,
        env_manager=None,
        build_manager=None,
        project_manager=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._env_manager = env_manager
        self._build_manager = build_manager
        self._project_manager = project_manager
        self._current_runner: LanguageRunner | None = None
        self._current_file: str = ""
        self._stdout_buffer: str = ""
        self._stderr_buffer: str = ""
        self._start_time: float = 0.0
        signals.run_file_requested.connect(self.run_file)
        signals.run_stop_requested.connect(self.stop)
        signals.run_project_requested.connect(self.run_project)
        signals.file_opened.connect(self._update_compiler_status)

        # Keep a persistent python runner for checking python version in status bar
        self._dummy_py = PythonRunner(self)

    @property
    def python_interpreter(self) -> str:
        return self._dummy_py.interpreter

    @property
    def current_compiler(self) -> str:
        if self._current_runner:
            return self._current_runner.interpreter
        return ""

    def _update_compiler_status(self, path: str) -> None:
        ext = Path(path).suffix.lower()
        runner = LanguageRunnerFactory.get_runner(ext, self)
        if runner:
            signals.compiler_updated.emit(runner.interpreter)
            runner.deleteLater()
        else:
            signals.compiler_updated.emit("")

    def run_file(self, path: str) -> None:
        """Execute a file through the full execution pipeline."""
        ext = Path(path).suffix.lower()
        runner = LanguageRunnerFactory.get_runner(ext, self)

        if not runner:
            signals.mission_update.emit("ERROR", f"No runner for {ext} files")
            return

        if self._current_runner:
            self._current_runner.stop()
            self._current_runner.deleteLater()

        self._current_runner = runner
        self._current_file = path
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._start_time = time.time()

        # Capture output for ExecutionEvent
        self._current_runner.output.connect(self._on_runner_output)
        self._current_runner.finished.connect(self._on_finished)

        name = Path(path).name
        signals.problems_updated.emit([])  # Clear problems before run
        signals.mission_update.emit("RUN", f"Running {name}...")
        self.run_started.emit(path)
        self._current_runner.run(path)

    def run_project(self) -> None:
        """Run the project's main file as defined in project metadata."""
        if not self._project_manager or not self._project_manager.current_path:
            signals.mission_update.emit("ERROR", "No project open")
            return

        project_path = self._project_manager.current_path
        metadata = self._project_manager.get_metadata(project_path)

        if metadata and metadata.main_file:
            main = project_path / metadata.main_file
            if main.exists():
                self.run_file(str(main))
                return

        # Fallback: auto-detect main file
        for candidate in ["main.py", "src/main.py", "index.js", "src/index.js",
                          "src/Main.java", "src/main.c", "src/main.cpp"]:
            main = project_path / candidate
            if main.exists():
                self.run_file(str(main))
                return

        signals.mission_update.emit("ERROR", "No main file found in project")

    def stop(self) -> None:
        if self._current_runner and self._current_runner.is_running():
            self._current_runner.stop()
            signals.mission_update.emit("STOP", "Execution stopped")

    def restart(self) -> None:
        self.stop()
        if self._current_file:
            self.run_file(self._current_file)

    def is_running(self) -> bool:
        return self._current_runner is not None and self._current_runner.is_running()

    def _on_runner_output(self, text: str, category: str) -> None:
        """Capture output for both the UI and the ExecutionEvent."""
        self.output.emit(text, category)
        if category in ("build",):
            pass  # Build output not captured in execution stdout
        else:
            self._stdout_buffer += text

    def _on_finished(self, exit_code: int) -> None:
        elapsed = time.time() - self._start_time
        name = Path(self._current_file).name if self._current_file else "file"

        if exit_code == 0:
            signals.mission_update.emit("DONE", f"{name} finished successfully")
        else:
            signals.mission_update.emit("ERROR", f"{name} exited with code {exit_code}")

        self.run_finished.emit(self._current_file, exit_code)

        # Emit canonical ExecutionEvent
        ext = Path(self._current_file).suffix.lower() if self._current_file else ""
        language_map = {
            ".py": "python", ".pyw": "python", ".js": "javascript",
            ".java": "java", ".c": "c", ".cpp": "cpp", ".cc": "cpp",
        }
        project_path = None
        env_name = None
        runtime_name = ""

        if self._project_manager and self._project_manager.current_path:
            project_path = str(self._project_manager.current_path)
        if self._env_manager:
            env = self._env_manager.get_active_environment()
            if env:
                env_name = env.name
                runtime_name = env.version

        import datetime
        event = ExecutionEvent(
            operation="run",
            file_path=self._current_file,
            project_path=project_path,
            working_directory=str(Path(self._current_file).parent) if self._current_file else "",
            language=language_map.get(ext, ext.lstrip(".")),
            runtime=runtime_name,
            environment=env_name,
            exit_code=exit_code,
            stdout=self._stdout_buffer,
            stderr=self._stderr_buffer,
            elapsed=elapsed,
            timestamp=datetime.datetime.now().isoformat(),
        )
        signals.execution_completed.emit(event)


# ---------------------------------------------------------------------------
# Backward compatibility alias
# ---------------------------------------------------------------------------
RunService = RunManager

