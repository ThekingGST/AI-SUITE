from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
from .context import DocumentStore
from .models import Document

class DocumentProcessorWorker(QThread):
    finished_doc = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, store: DocumentStore, filepath: Path):
        super().__init__()
        self.store = store
        self.filepath = filepath

    def run(self):
        try:
            doc = self.store.attach_file(self.filepath)
            self.finished_doc.emit(doc)
        except Exception as e:
            self.error.emit(str(e))
