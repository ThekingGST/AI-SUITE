from __future__ import annotations


HOLOGRAM_QSS = """
QMainWindow, QWidget {
    background: #071014;
    color: #d7fbff;
    font-family: Segoe UI, Arial;
    font-size: 13px;
}
QFrame#Panel {
    background: rgba(8, 35, 44, 190);
    border: 1px solid #22d8ff;
    border-radius: 8px;
}
QTextEdit, QListWidget, QLineEdit {
    background: rgba(2, 15, 22, 210);
    border: 1px solid #138fb1;
    border-radius: 6px;
    color: #d7fbff;
    selection-background-color: #22d8ff;
}
QPushButton {
    background: #0b5164;
    border: 1px solid #22d8ff;
    border-radius: 6px;
    color: #e8fdff;
    padding: 8px 12px;
}
QPushButton:hover {
    background: #0f6f87;
}
QPushButton:pressed {
    background: #083a48;
}
QProgressBar {
    background: #031318;
    border: 1px solid #138fb1;
    border-radius: 4px;
    height: 12px;
    text-align: center;
}
QProgressBar::chunk {
    background: #22d8ff;
    border-radius: 3px;
}
"""
