"""Execution Manager — orchestrates file execution via TerminalService."""

from PyQt5.QtCore import QObject, pyqtSignal
import time
from pathlib import Path

from friday_ai.services.execution_terminal_service import ExecutionTerminalService
from friday_ai.services.interpreter_manager import InterpreterManager
from friday_ai.services.diagnostics_service import DiagnosticsService
from shared.logger import get_logger

LOG = get_logger("friday.execution_manager")

class ExecutionManager(QObject):
    """Manages the execution lifecycle of files and processes."""
    
    output_ready = pyqtSignal(str, str) # text, category
    execution_started = pyqtSignal()
    execution_finished = pyqtSignal(int, float)
    diagnostic_available = pyqtSignal(str, str)
    
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.terminal = ExecutionTerminalService(self)
        self.interpreter_mgr = InterpreterManager()
        self.diagnostics = DiagnosticsService()
        
        self._start_time = 0.0
        
        # Connect TerminalService signals
        self.terminal.stdout_ready.connect(self._on_stdout)
        self.terminal.stderr_ready.connect(self._on_stderr)
        self.terminal.process_started.connect(self._on_started)
        self.terminal.process_finished.connect(self._on_finished)
        self.terminal.process_error.connect(self._on_error)

    def run_file(self, file_path: str) -> None:
        """Run a specific file."""
        if self.terminal.is_running():
            self.output_ready.emit("A process is already running. Stop it first.\n", "system")
            return
            
        path = Path(file_path)
        if not path.exists():
            self.output_ready.emit(f"File not found: {file_path}\n", "system")
            return

        # Determine how to run based on extension (Future extensibility here)
        if path.suffix == ".py":
            self._run_python(path)
        else:
            self.output_ready.emit(f"Execution not supported for extension: {path.suffix}\n", "system")

    def _run_python(self, path: Path) -> None:
        if not self.interpreter_mgr.has_python():
            # Missing Python fallback
            msg = (
                "Python interpreter not found.\n\n"
                "Checked:\n"
                "✓ python\n"
                "✓ py\n"
                "✓ python3\n\n"
                "No interpreter detected.\n"
                "Please install Python 3.11+ or configure an interpreter.\n"
            )
            self.output_ready.emit(msg, "stderr")
            return

        python_exe = self.interpreter_mgr.get_python_path()
        self.diagnostics.reset()
        self.terminal.set_cwd(str(path.parent.absolute()))
        
        self.output_ready.emit(f"> {Path(python_exe).name} {path.name}\n\n", "system")
        self.terminal.run_command(python_exe, [path.name])

    def stop_execution(self) -> None:
        """Stop the running process."""
        self.terminal.terminate()

    def _on_stdout(self, text: str) -> None:
        self.output_ready.emit(text, "stdout")

    def _on_stderr(self, text: str) -> None:
        self.diagnostics.analyze_stderr_chunk(text)
        self.output_ready.emit(text, "stderr")

    def _on_started(self) -> None:
        self._start_time = time.time()
        self.execution_started.emit()

    def _on_finished(self, exit_code: int, status_str: str) -> None:
        time_taken = time.time() - self._start_time
        
        # Display exit code
        self.output_ready.emit(f"\nExit Code : {exit_code} ({status_str})\n", "system")
        self.output_ready.emit(f"Execution Time : {time_taken:.2f} sec\n", "system")
        
        self.execution_finished.emit(exit_code, time_taken)
        
        # Check diagnostics
        if self.diagnostics.has_error():
            friendly_msg = self.diagnostics.get_friendly_diagnostic()
            if friendly_msg:
                self.diagnostic_available.emit(friendly_msg, self.diagnostics.get_raw_stderr())

    def _on_error(self, err_msg: str) -> None:
        self.output_ready.emit(f"\nProcess Error: {err_msg}\n", "stderr")
