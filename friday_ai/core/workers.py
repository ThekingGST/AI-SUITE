"""Reusable background worker for non-blocking operations.

Any expensive computation (file scanning, project indexing, etc.) should be
dispatched to a ``BackgroundWorker`` so the UI thread is never blocked.

Usage::

    from friday_ai.core.workers import BackgroundWorker

    def heavy_work():
        return count_files("/some/path")

    worker = BackgroundWorker(heavy_work)
    worker.result_ready.connect(lambda result: print(f"Found {result} files"))
    worker.start()
"""

from __future__ import annotations

from typing import Any, Callable

from PyQt5.QtCore import QThread, pyqtSignal as Signal


class BackgroundWorker(QThread):
    """Run a callable on a background thread and emit the result.

    The worker is a ``QThread`` so that its ``result_ready`` signal is safe to
    connect to Qt slots for UI updates.

    **Note:** The signal is named ``result_ready`` (not ``finished``) to avoid
    shadowing ``QThread.finished``.

    Parameters
    ----------
    fn:
        The callable to execute on the background thread.
    *args:
        Positional arguments forwarded to *fn*.
    parent:
        Optional QObject parent for lifetime management.
    """

    result_ready = Signal(object)

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._result: Any = None

    @property
    def result(self) -> Any:
        """The result of the callable, available after the thread finishes."""
        return self._result

    def run(self) -> None:
        try:
            self._result = self._fn(*self._args)
        except Exception as exc:
            self._result = exc
        self.result_ready.emit(self._result)
