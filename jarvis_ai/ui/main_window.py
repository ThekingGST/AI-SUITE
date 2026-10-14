from __future__ import annotations

import threading
import time

import psutil
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai.memory import MemoryStore
from ai.ollama_brain import OllamaBrain
from config import ensure_directories
from ui.hologram_ui import cv_to_pixmap
from ui.themes import HOLOGRAM_QSS
from ui.widgets import MetricPanel, Panel, RadarWidget, StatusPill, WaveformWidget
from utils.constants import BOOT_LINES
from utils.logger import LOGGER
from vision.camera import CameraSystem
from voice.command_router import CommandRouter
from voice.listener import TextCommandBus, VoiceListener
from voice.speaker import Speaker
from voice.wakeword import WakeWordDetector


class MainWindow(QMainWindow):
    append_chat = pyqtSignal(str, str)
    append_log = pyqtSignal(str)
    set_status = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        ensure_directories()
        self.setWindowTitle("JARVIS AI Desktop Assistant")
        self.resize(1380, 820)
        self.setStyleSheet(HOLOGRAM_QSS)

        self.memory = MemoryStore()
        self.brain = OllamaBrain(self.memory)
        self.speaker = Speaker()
        self.tts_enabled = True
        self.command_bus = TextCommandBus()
        self.wakeword = WakeWordDetector()
        self.camera = CameraSystem(on_event=self._vision_event)
        self.router = CommandRouter(
            self.brain,
            self.memory,
            self.speaker,
            on_response=lambda text: self.append_chat.emit("JARVIS", text),
            on_vision_command=self._vision_command,
        )
        self.listener = VoiceListener(self._voice_text)
        self._command_stop = threading.Event()
        self._command_thread = threading.Thread(target=self._command_loop, name="JarvisCommandLoop", daemon=True)

        self._build_ui()
        self._wire_timers()
        self.append_chat.connect(self._append_chat)
        self.append_log.connect(self._append_log)
        self.set_status.connect(self._set_status)

        self.camera.start()
        self.listener.start()
        self._command_thread.start()
        self._boot()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QGridLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        self.camera_label = QLabel("CAMERA OFFLINE")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(760, 430)
        camera_panel = Panel()
        camera_layout = QVBoxLayout(camera_panel)
        self.fps_label = QLabel("FPS 0.0")
        camera_layout.addWidget(self.fps_label)
        camera_layout.addWidget(self.camera_label, 1)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.status_pill = StatusPill()
        self.waveform = WaveformWidget()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Type a command or question...")
        self.command_input.returnPressed.connect(self._submit_text_command)
        send_button = QPushButton("Transmit")
        send_button.clicked.connect(self._submit_text_command)
        input_row = QHBoxLayout()
        input_row.addWidget(self.command_input, 1)
        input_row.addWidget(send_button)
        chat_panel = Panel()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.addWidget(QLabel("AI CONSOLE"))
        chat_layout.addWidget(self.status_pill)
        chat_layout.addWidget(self.chat, 1)
        chat_layout.addWidget(self.waveform)
        chat_layout.addLayout(input_row)

        self.logs = QListWidget()
        log_panel = Panel()
        log_layout = QVBoxLayout(log_panel)
        log_layout.addWidget(QLabel("SYSTEM LOGS"))
        log_layout.addWidget(self.logs)

        self.cpu_panel = MetricPanel("CPU")
        self.ram_panel = MetricPanel("RAM")
        self.radar = RadarWidget()
        radar_panel = Panel()
        radar_layout = QVBoxLayout(radar_panel)
        radar_layout.addWidget(QLabel("HOLOGRAM RADAR"))
        radar_layout.addWidget(self.radar, 1)

        controls = Panel()
        control_layout = QHBoxLayout(controls)
        for label, callback in (
            ("Objects", self._toggle_objects),
            ("Photo", self._take_photo),
            ("Refresh LLM", self._refresh_llm),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            control_layout.addWidget(button)
        self.mute_button = QPushButton("Mute")
        self.mute_button.clicked.connect(self._toggle_tts)
        self._update_mute_button()
        control_layout.insertWidget(2, self.mute_button)

        root.addWidget(camera_panel, 0, 0, 2, 2)
        root.addWidget(chat_panel, 0, 2, 3, 1)
        root.addWidget(self.cpu_panel, 2, 0)
        root.addWidget(self.ram_panel, 2, 1)
        root.addWidget(radar_panel, 3, 0, 1, 1)
        root.addWidget(log_panel, 3, 1, 1, 2)
        root.addWidget(controls, 4, 0, 1, 3)
        self.setCentralWidget(central)

    def _wire_timers(self) -> None:
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.start(33)
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self._update_metrics)
        self.metrics_timer.start(1000)

    def _boot(self) -> None:
        for i, line in enumerate(BOOT_LINES):
            QTimer.singleShot(i * 450, lambda msg=line: self.append_log.emit(msg))
        QTimer.singleShot(len(BOOT_LINES) * 450, lambda: self._notify("JARVIS online."))

    def _voice_text(self, text: str) -> None:
        if self.speaker.recently_spoke() and self.wakeword.contains_wake_word(text):
            self.append_log.emit("Ignored microphone echo from speaker output.")
            return
        self.append_log.emit(f"Heard: {text}")
        if self.wakeword.contains_wake_word(text):
            self.set_status.emit("Listening")
            command = self.wakeword.strip_wake_word(text)
            if command:
                self.command_bus.submit(command)
            else:
                self.speaker.speak("Yes?")

    def _command_loop(self) -> None:
        while not self._command_stop.is_set():
            command = self.command_bus.get(timeout=0.2)
            if not command:
                continue
            self.append_chat.emit("YOU", command)
            self.set_status.emit("AI thinking")
            self.router.handle(command)
            self.set_status.emit("Systems online")

    def _submit_text_command(self) -> None:
        text = self.command_input.text().strip()
        if text:
            self.command_input.clear()
            self.command_bus.submit(text)

    def _update_frame(self) -> None:
        frame = self.camera.latest_frame()
        if frame is None:
            return
        pixmap = cv_to_pixmap(frame)
        self.camera_label.setPixmap(pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.fps_label.setText(f"FPS {self.camera.fps:.1f}")

    def _update_metrics(self) -> None:
        self.cpu_panel.set_value(psutil.cpu_percent(interval=None))
        self.ram_panel.set_value(psutil.virtual_memory().percent)

    def _append_chat(self, who: str, text: str) -> None:
        if who == "JARVIS":
            self._type_response(who, text)
        else:
            self.chat.append(f"<b>{who}:</b> {text}")

    def _type_response(self, who: str, text: str) -> None:
        self.chat.append(f"<b>{who}:</b> ")
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat.setTextCursor(cursor)
        chunks = [text[index : index + 3] for index in range(0, len(text), 3)]

        def add_next() -> None:
            if not chunks:
                self.chat.append("")
                return
            self.chat.insertPlainText(chunks.pop(0))
            self.chat.moveCursor(QTextCursor.End)
            QTimer.singleShot(12, add_next)

        add_next()

    def _append_log(self, text: str) -> None:
        self.logs.addItem(time.strftime("%H:%M:%S") + "  " + text)
        self.logs.scrollToBottom()
        LOGGER.info(text)

    def _set_status(self, text: str) -> None:
        self.status_pill.set_status(text)
        self.waveform.set_active("listening" in text.lower() or "thinking" in text.lower())

    def _vision_event(self, text: str) -> None:
        self._notify(text)

    def _vision_command(self, command: str) -> str:
        if command == "objects":
            return self.camera.describe_objects()
        return "Unknown vision command."

    def _toggle_objects(self) -> None:
        self.camera.vision.enabled_object_detection = not self.camera.vision.enabled_object_detection
        self._notify(f"Object detection {'enabled' if self.camera.vision.enabled_object_detection else 'disabled'}.")

    def _take_photo(self) -> None:
        self._notify("Photo saved: " + self.camera.capture_photo())

    def _refresh_llm(self) -> None:
        model = self.brain.refresh_model()
        self._notify(f"LLM model: {model or 'offline fallback'}")

    def _toggle_tts(self) -> None:
        self.tts_enabled = not self.tts_enabled
        self.speaker.set_enabled(self.tts_enabled)
        self._update_mute_button()
        if self.tts_enabled:
            self._notify("Voice systems online.")
        else:
            self.append_log.emit("Voice output disabled.")

    def _notify(self, text: str) -> None:
        self.append_log.emit(text)
        self.speaker.speak(text)

    def _update_mute_button(self) -> None:
        if self.tts_enabled:
            self.mute_button.setText("Mute")
            glow_color = QColor(34, 216, 255, 210)
            self.mute_button.setStyleSheet(
                "QPushButton {"
                "background: #0b5164;"
                "border: 1px solid #22d8ff;"
                "border-radius: 6px;"
                "color: #e8fdff;"
                "padding: 8px 12px;"
                "}"
                "QPushButton:hover { background: #0f6f87; }"
            )
        else:
            self.mute_button.setText("Unmute")
            glow_color = QColor(255, 64, 87, 220)
            self.mute_button.setStyleSheet(
                "QPushButton {"
                "background: #6b1018;"
                "border: 1px solid #ff4057;"
                "border-radius: 6px;"
                "color: #ffe8ec;"
                "padding: 8px 12px;"
                "}"
                "QPushButton:hover { background: #8b1621; }"
            )
        glow = QGraphicsDropShadowEffect(self.mute_button)
        glow.setBlurRadius(22)
        glow.setOffset(0, 0)
        glow.setColor(glow_color)
        self.mute_button.setGraphicsEffect(glow)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._command_stop.set()
        self.listener.stop()
        self.camera.stop()
        self.speaker.close()
        event.accept()


def run_app() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec_()
