"""Run service — executes files through language-specific runners.

Architecture:
    RunService → LanguageRunnerFactory → Language Runners
"""
from __future__ import annotations
import os
import re
import shutil
import sys
import time
from pathlib import Path
from PyQt5.QtCore import QObject, QProcess, pyqtSignal as Signal

from friday_ai.core.signals import signals
from shared.logger import get_logger
from friday_ai.ui.panels.problems_panel import Problem

LOG = get_logger("friday.run")


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


class RunService(QObject):
    """Manages file execution through language-specific runners."""
    output = Signal(str, str)
    run_started = Signal(str)   # file path
    run_finished = Signal(str, int)  # file path, exit code

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_runner: LanguageRunner | None = None
        self._current_file: str = ""
        signals.run_file_requested.connect(self.run_file)
        signals.run_stop_requested.connect(self.stop)
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
        ext = Path(path).suffix.lower()
        runner = LanguageRunnerFactory.get_runner(ext, self)
        
        if not runner:
            signals.mission_update.emit("ERROR", f"No runner for {ext} files")
            return
            
        if self._current_runner:
            self._current_runner.stop()
            self._current_runner.deleteLater()
            
        self._current_runner = runner
        self._current_runner.output.connect(self.output.emit)
        self._current_runner.finished.connect(self._on_finished)
        
        self._current_file = path
        name = Path(path).name
        
        signals.problems_updated.emit([]) # Clear problems before run
        signals.mission_update.emit("RUN", f"Running {name}...")
        self.run_started.emit(path)
        self._current_runner.run(path)

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

    def _on_finished(self, exit_code: int) -> None:
        name = Path(self._current_file).name if self._current_file else "file"
        if exit_code == 0:
            signals.mission_update.emit("DONE", f"{name} finished successfully")
        else:
            signals.mission_update.emit("ERROR", f"{name} exited with code {exit_code}")
        self.run_finished.emit(self._current_file, exit_code)
