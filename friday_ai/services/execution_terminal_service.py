"""Execution Terminal Service — asynchronous shell execution using QProcess.
Placed here to avoid overwriting the existing terminal_service.py (which handles UI terminals).
"""

from PyQt5.QtCore import QObject, pyqtSignal, QProcess, QProcessEnvironment
import os
import platform
from shared.logger import get_logger

LOG = get_logger("friday.execution_terminal")

class ExecutionTerminalService(QObject):
    """Wraps QProcess to execute shell commands asynchronously."""

    stdout_ready = pyqtSignal(str)
    stderr_ready = pyqtSignal(str)
    process_started = pyqtSignal()
    process_finished = pyqtSignal(int, str)
    process_error = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.SeparateChannels)
        
        self._process.readyReadStandardOutput.connect(self._on_ready_read_stdout)
        self._process.readyReadStandardError.connect(self._on_ready_read_stderr)
        self._process.started.connect(lambda: self.process_started.emit())
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        self._current_cwd = os.getcwd()

    def set_cwd(self, cwd: str) -> None:
        if os.path.exists(cwd):
            self._current_cwd = cwd
            self._process.setWorkingDirectory(cwd)

    def run_command(self, command: str, args: list[str]) -> bool:
        if self._process.state() != QProcess.NotRunning:
            return False

        env = QProcessEnvironment.systemEnvironment()
        self._process.setProcessEnvironment(env)
        
        self._process.start(command, args)
        return True

    def terminate(self) -> None:
        if self._process.state() != QProcess.NotRunning:
            if platform.system() == "Windows":
                self._process.kill()
            else:
                self._process.terminate()

    def is_running(self) -> bool:
        return self._process.state() != QProcess.NotRunning

    def _on_ready_read_stdout(self) -> None:
        data = self._process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        self.stdout_ready.emit(text)

    def _on_ready_read_stderr(self) -> None:
        data = self._process.readAllStandardError()
        text = bytes(data).decode('utf-8', errors='replace')
        self.stderr_ready.emit(text)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        status_str = "Normal" if exit_status == QProcess.NormalExit else "Crash"
        self.process_finished.emit(exit_code, status_str)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        error_msgs = {
            QProcess.FailedToStart: "Failed to start (is it installed and in PATH?)",
            QProcess.Crashed: "Process crashed.",
            QProcess.Timedout: "Process timed out.",
            QProcess.WriteError: "Write error.",
            QProcess.ReadError: "Read error.",
            QProcess.UnknownError: "Unknown error."
        }
        self.process_error.emit(error_msgs.get(error, f"Error Code {error}"))
