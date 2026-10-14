"""Terminal session management.

Manages shell processes (PowerShell, CMD, Git Bash) via QProcess.
Each terminal session is independent and can be started/stopped.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from PyQt5.QtCore import QObject, QProcess, pyqtSignal as Signal
from shared.logger import get_logger

LOG = get_logger("friday.terminal")


def detect_shells() -> list[tuple[str, str]]:
    """Detect available shells. Returns list of (name, executable_path)."""
    shells = []
    # PowerShell (always available on Windows)
    ps_path = shutil.which("powershell")
    if ps_path:
        shells.append(("PowerShell", ps_path))
    # CMD
    cmd_path = shutil.which("cmd")
    if cmd_path:
        shells.append(("CMD", cmd_path))
    # Git Bash
    git_bash_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for p in git_bash_paths:
        if Path(p).exists():
            shells.append(("Git Bash", p))
            break
    # Fallback
    if not shells:
        shells.append(("PowerShell", "powershell"))
    return shells


class TerminalSession(QObject):
    """A single terminal session backed by QProcess."""
    output_received = Signal(str)
    finished = Signal(int)  # exit code

    def __init__(self, shell_path: str, cwd: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process = QProcess(self)
        self._shell_path = shell_path
        self._cwd = cwd or str(Path.home())
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)

    def start(self) -> None:
        self._process.setWorkingDirectory(self._cwd)
        # PowerShell needs -NoLogo for clean output
        if "powershell" in self._shell_path.lower():
            self._process.start(self._shell_path, ["-NoLogo", "-NoProfile"])
        elif "cmd" in self._shell_path.lower():
            self._process.start(self._shell_path, [])
        else:
            self._process.start(self._shell_path, ["--login"])
        LOG.info("Terminal started: %s in %s", self._shell_path, self._cwd)

    def write(self, text: str) -> None:
        if self._process.state() == QProcess.ProcessState.Running:
            import os
            newline = "\r\n" if os.name == "nt" else "\n"
            self._process.write((text + newline).encode("utf-8"))

    def kill(self) -> None:
        if self._process.state() == QProcess.ProcessState.Running:
            self._process.kill()

    def is_running(self) -> bool:
        return self._process.state() == QProcess.ProcessState.Running

    def _on_output(self) -> None:
        data = self._process.readAllStandardOutput().data()
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = str(data)
        self.output_received.emit(text)

    def _on_finished(self, exit_code: int, _status) -> None:
        self.finished.emit(exit_code)
        LOG.info("Terminal exited with code %d", exit_code)
