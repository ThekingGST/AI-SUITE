from __future__ import annotations

import importlib.util
import threading
import time

import psutil
from PyQt5.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
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
from ui.ai_core_orb import AICoreOrb, OrbState
from ui.hologram_ui import cv_to_pixmap, offline_hologram_pixmap
from ui.themes import HOLOGRAM_QSS
from ui.widgets import MetricPanel, Panel, StatusPill, WaveformWidget
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
    registration_done = pyqtSignal(str)

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
        self.mic_enabled = True
        self.camera_enabled = True
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
        self._was_speaking = False
        self._mic_paused_for_speech = False
        self._offline_tick = 0
        self._command_thread = threading.Thread(target=self._command_loop, name="JarvisCommandLoop", daemon=True)

        self._build_ui()
        self._wire_timers()
        self.append_chat.connect(self._append_chat)
        self.append_log.connect(self._append_log)
        self.set_status.connect(self._set_status)
        self.registration_done.connect(lambda msg: self._notify(msg, speak=True))

        self.camera.start()
        self.listener.start()
        self._command_thread.start()
        self._boot()
        threading.Thread(target=self._run_startup_diagnostics, name="JarvisDiagnostics", daemon=True).start()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QGridLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        self.camera_label = QLabel("CAMERA OFFLINE")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(760, 430)
        self.ai_orb = AICoreOrb()
        self.ai_orb.setFixedSize(148, 148)
        self.ai_orb.setAttribute(Qt.WA_TransparentForMouseEvents)
        camera_panel = Panel()
        camera_layout = QVBoxLayout(camera_panel)
        self.fps_label = QLabel("FPS 0.0")
        camera_layout.addWidget(self.fps_label)
        camera_view = QWidget()
        self.camera_view_layout = QGridLayout(camera_view)
        self.camera_view_layout.setContentsMargins(0, 0, 0, 0)
        self.camera_view_layout.addWidget(self.camera_label, 0, 0)
        self.camera_view_layout.addWidget(self.ai_orb, 0, 0, Qt.AlignHCenter | Qt.AlignBottom)
        camera_layout.addWidget(camera_view, 1)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.status_pill = StatusPill()
        self.waveform = WaveformWidget()
        self.speaking_indicator = QLabel("Speaking: Idle")
        self.listening_indicator = QLabel("Listening: Ready")
        self.muted_indicator = QLabel("Voice: Online")
        self.mic_indicator = QLabel("Mic: Active")
        self.detection_indicator = QLabel("Detection Disabled")
        self.identity_indicator = QLabel("Identity: UNKNOWN")
        self.confidence_indicator = QLabel("Confidence: 0.00")
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
        indicator_row = QHBoxLayout()
        for indicator in (
            self.speaking_indicator,
            self.listening_indicator,
            self.muted_indicator,
            self.mic_indicator,
            self.detection_indicator,
            self.identity_indicator,
            self.confidence_indicator,
        ):
            indicator.setAlignment(Qt.AlignCenter)
            indicator_row.addWidget(indicator)
        chat_layout.addLayout(indicator_row)
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
        controls = Panel()
        control_layout = QHBoxLayout(controls)
        self.camera_button = QPushButton("Disable Camera")
        self.camera_button.clicked.connect(self._toggle_camera)
        self._style_camera_button(active=True)
        control_layout.addWidget(self.camera_button)
        self.object_button = QPushButton("Enable Object Detection")
        self.object_button.clicked.connect(self._toggle_objects)
        self._update_object_button()
        control_layout.addWidget(self.object_button)
        for label, callback in (
            ("Photo", self._take_photo),
            ("Register Face", self._register_face_prompt),
            ("Refresh LLM", self._refresh_llm),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            control_layout.addWidget(button)
        self.mute_button = QPushButton("Mute")
        self.mute_button.clicked.connect(self._toggle_tts)
        self._update_mute_button()
        control_layout.insertWidget(2, self.mute_button)
        self.mic_button = QPushButton("Mic ON")
        self.mic_button.clicked.connect(self._toggle_mic)
        self._update_mic_button()
        control_layout.insertWidget(3, self.mic_button)
        self.voice_mode_button = QPushButton("Standard Voice")
        self.voice_mode_button.clicked.connect(self._toggle_voice_mode)
        self._update_voice_mode_button()
        control_layout.insertWidget(4, self.voice_mode_button)

        root.addWidget(camera_panel, 0, 0, 2, 2)
        root.addWidget(chat_panel, 0, 2, 3, 1)
        root.addWidget(self.cpu_panel, 2, 0)
        root.addWidget(self.ram_panel, 2, 1)
        root.addWidget(log_panel, 3, 0, 1, 3)
        root.addWidget(controls, 4, 0, 1, 3)
        self.setCentralWidget(central)

    def _wire_timers(self) -> None:
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._update_frame)
        self.frame_timer.start(33)
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self._update_metrics)
        self.metrics_timer.start(1000)
        self.indicator_timer = QTimer(self)
        self.indicator_timer.timeout.connect(self._update_live_indicators)
        self.indicator_timer.start(120)

    def _boot(self) -> None:
        for i, line in enumerate(BOOT_LINES):
            QTimer.singleShot(i * 450, lambda msg=line: self.append_log.emit(msg))
        QTimer.singleShot(len(BOOT_LINES) * 450, lambda: self._notify("JARVIS online.", speak=True))

    def _voice_text(self, text: str) -> None:
        print("RAW VOICE:", text)
        LOGGER.info("RAW VOICE: %s", text)
        if not self.mic_enabled:
            return
        if self.speaker.recently_spoke() and self.wakeword.contains_wake_word(text):
            self.append_log.emit("Ignored microphone echo from speaker output.")
            return
        self.append_log.emit(f"Heard: {text}")
        if self.wakeword.contains_wake_word(text):
            self.set_status.emit("Listening")
            command = self.wakeword.strip_wake_word(text)
            if command:
                LOGGER.info("ROUTING COMMAND: %s", command)
                self.command_bus.submit(command)
            else:
                print("DEBUG TTS:", "Yes?")
                self.speaker.speak("Yes?")

    def _command_loop(self) -> None:
        while not self._command_stop.is_set():
            command = self.command_bus.get(timeout=0.2)
            if not command:
                continue
            try:
                self.append_chat.emit("YOU", command)
                self.set_status.emit("AI thinking")
                self.ai_orb.set_state(OrbState.THINKING)
                self._sync_tts_state()
                LOGGER.info("ROUTING COMMAND: %s", command)
                self.router.handle(command)
            except Exception as exc:
                LOGGER.exception("Command loop failure: %s", exc)
                message = f"Command execution failed: {exc}"
                self.append_chat.emit("JARVIS", message)
                print("DEBUG TTS:", message)
                self.speaker.speak(message)
            finally:
                self.set_status.emit("Systems online")

    def _submit_text_command(self) -> None:
        text = self.command_input.text().strip()
        if text:
            self.command_input.clear()
            self.command_bus.submit(text)

    def _update_frame(self) -> None:
        frame = self.camera.latest_frame()
        if frame is None:
            self._offline_tick += 1
            self.ai_orb.set_state(OrbState.CAMERA_DISABLED if not self.camera_enabled else OrbState.OFFLINE)
            self.camera_label.setPixmap(
                offline_hologram_pixmap(self.camera_label.width(), self.camera_label.height(), self._offline_tick)
            )
            self.fps_label.setText("CAMERA OFFLINE" if not self.camera_enabled else "CAMERA INITIALIZING")
            return
        pixmap = cv_to_pixmap(frame)
        self.camera_label.setPixmap(pixmap.scaled(self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.fps_label.setText(f"FPS {self.camera.fps:.1f}")
        self._position_orb(frame)

    def _update_metrics(self) -> None:
        self.cpu_panel.set_value(psutil.cpu_percent(interval=None))
        self.ram_panel.set_value(psutil.virtual_memory().percent)

    def _update_live_indicators(self) -> None:
        self._sync_mic_with_speech()
        if self.speaker.is_speaking:
            self.ai_orb.set_state(OrbState.SPEAKING)
        if self.speaker.is_speaking and not self._was_speaking:
            self.append_log.emit("Speaking...")
        if not self.speaker.is_speaking and self._was_speaking:
            self.ai_orb.set_state(OrbState.IDLE if self.camera_enabled else OrbState.CAMERA_DISABLED)
        self._was_speaking = self.speaker.is_speaking
        self._style_indicator(
            self.speaking_indicator,
            "Speaking..." if self.speaker.is_speaking else "Speaking: Idle",
            self.speaker.is_speaking,
        )
        if self.tts_enabled:
            mode_label = "Premium" if self.speaker.voice_mode == "premium" else "Standard"
            engine = self.speaker.active_engine_name.title()
            self._style_indicator(self.muted_indicator, f"Voice: {mode_label} ({engine})", True)
        else:
            self.muted_indicator.setText("Muted")
            self.muted_indicator.setStyleSheet("color: #ffe8ec; border: 1px solid #ff4057; border-radius: 5px; padding: 3px; background: rgba(95, 15, 24, 150);")
        if self.mic_enabled:
            self._style_indicator(self.mic_indicator, "Mic: Active", True)
        else:
            self.mic_indicator.setText("Mic: Muted")
            self.mic_indicator.setStyleSheet("color: #ffe8ec; border: 1px solid #ff4057; border-radius: 5px; padding: 3px; background: rgba(95, 15, 24, 150);")
        self._style_indicator(
            self.detection_indicator,
            "Detection Active" if self.camera.vision.object_detection_enabled else "Detection Disabled",
            self.camera.vision.object_detection_enabled,
        )
        snapshot = self.camera.vision.snapshot()
        known = [(label, score) for _, label, score in snapshot.identities if label != "unknown"]
        if known:
            name, score = max(known, key=lambda item: item[1])
            self._style_indicator(self.identity_indicator, f"Identity: {name.upper()}", True)
            self._style_indicator(self.confidence_indicator, f"Confidence: {score:.2f}", True)
        else:
            self._style_indicator(self.identity_indicator, "Identity: UNKNOWN", False)
            self._style_indicator(self.confidence_indicator, "Confidence: 0.00", False)

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
        self._style_indicator(self.listening_indicator, "Listening" if "listening" in text.lower() else "Listening: Ready", "listening" in text.lower())
        lowered = text.lower()
        if "listening" in lowered:
            self.ai_orb.set_state(OrbState.LISTENING)
        elif "thinking" in lowered:
            self.ai_orb.set_state(OrbState.THINKING)
        elif not self.speaker.is_speaking:
            self.ai_orb.set_state(OrbState.IDLE if self.camera_enabled else OrbState.CAMERA_DISABLED)

    def _vision_event(self, text: str) -> None:
        self._notify(text, speak=text.startswith("Welcome back"))

    def _vision_command(self, command: str) -> str:
        if command == "objects":
            return self.camera.describe_objects()
        return "Unknown vision command."

    def _toggle_camera(self) -> None:
        self.camera_enabled = not self.camera_enabled
        if self.camera_enabled:
            self.camera.start()
            self.camera_button.setText("Disable Camera")
            self._style_camera_button(active=True)
            self._notify("Camera enabled", speak=False)
        else:
            self.camera.vision.set_object_detection_enabled(False)
            self.camera.stop()
            self._update_object_button()
            self.camera_button.setText("Enable Camera")
            self._style_camera_button(active=False)
            self._notify("Camera disabled", speak=False)

    def _toggle_objects(self) -> None:
        enabled = not self.camera.vision.object_detection_enabled
        self.camera.vision.set_object_detection_enabled(enabled)
        self._update_object_button()
        self._notify("Object detection enabled" if enabled else "Object detection disabled", speak=False)

    def _take_photo(self) -> None:
        self._notify("Photo saved: " + self.camera.capture_photo(), speak=True)

    def _refresh_llm(self) -> None:
        model = self.brain.refresh_model()
        self._notify(f"LLM model: {model or 'offline fallback'}", speak=False)

    def _register_face_prompt(self) -> None:
        name, ok = QInputDialog.getText(self, "Register Face", "Name:")
        if not ok or not name.strip():
            return
        threading.Thread(
            target=self._register_face_worker,
            args=(name.strip(),),
            name="JarvisFaceRegistration",
            daemon=True,
        ).start()

    def _register_face_worker(self, name: str) -> None:
        samples = []
        target_samples = 12
        deadline = time.time() + 7.0
        self.append_log.emit(f"Starting face registration for {name.title()}.")
        while time.time() < deadline and len(samples) < target_samples:
            frame = self.camera.latest_frame()
            if frame is None:
                time.sleep(0.15)
                continue
            faces = self.camera.vision.face_detector.detect(frame)
            if faces:
                self.append_log.emit("FACE DETECTED")
                samples.append((frame, faces[0]))
                self.append_log.emit(f"CAPTURED IMAGE {len(samples)}/{target_samples}")
            time.sleep(0.2)
        try:
            saved = self.camera.vision.face_recognizer.register_person(name, samples)
            if saved:
                self.registration_done.emit(f"Registered {saved} face samples for {name.title()}.")
            else:
                self.registration_done.emit("REGISTRATION FAILED: no embeddings generated.")
        except Exception as exc:
            LOGGER.exception("Face registration failed: %s", exc)
            self.registration_done.emit(f"REGISTRATION FAILED: {exc}")

    def _toggle_tts(self) -> None:
        self.tts_enabled = not self.tts_enabled
        self.speaker.set_enabled(self.tts_enabled)
        self._update_mute_button()
        LOGGER.info("Speaker Active" if self.tts_enabled else "Speaker Muted")
        if self.tts_enabled:
            self._notify("Voice systems online.", speak=True)
        else:
            self.append_log.emit("Voice output disabled.")

    def _toggle_mic(self) -> None:
        self.mic_enabled = not self.mic_enabled
        if self.mic_enabled:
            self.listener.start()
            self._notify("Microphone enabled", speak=False)
        else:
            self.listener.stop()
            self._notify("Microphone disabled", speak=False)
        LOGGER.info("Mic Active" if self.mic_enabled else "Mic Muted")
        self._update_mic_button()

    def _toggle_voice_mode(self) -> None:
        new_mode = "premium" if self.speaker.voice_mode == "standard" else "standard"
        self.speaker.set_voice_mode(new_mode)
        self._update_voice_mode_button()
        mode_label = "Premium (Jarvis)" if new_mode == "premium" else "Standard (Offline)"
        LOGGER.info("Voice mode: %s", mode_label)
        self._notify(f"Voice mode: {mode_label}", speak=True)

    def _sync_tts_state(self) -> None:
        if self.speaker.enabled != self.tts_enabled:
            self.speaker.set_enabled(self.tts_enabled)

    def _notify(self, text: str, speak: bool = False) -> None:
        self.append_log.emit(text)
        if speak:
            print("DEBUG TTS:", text)
            self.speaker.speak(text)

    def _sync_mic_with_speech(self) -> None:
        if self.speaker.is_speaking and self.mic_enabled and not self._mic_paused_for_speech:
            self.listener.pause()
            self._mic_paused_for_speech = True
            self.append_log.emit("MIC PAUSED")
        elif not self.speaker.is_speaking and self._mic_paused_for_speech:
            self._mic_paused_for_speech = False
            if self.mic_enabled:
                self.listener.resume()
                self.append_log.emit("MIC RESUMED")

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

    def _update_mic_button(self) -> None:
        if self.mic_enabled:
            self.mic_button.setText("Mic ON")
            glow_color = QColor(34, 216, 255, 210)
            self.mic_button.setStyleSheet(
                "QPushButton {background: #0b5164; border: 1px solid #22d8ff; border-radius: 6px; color: #e8fdff; padding: 8px 12px;}"
                "QPushButton:hover { background: #0f6f87; }"
            )
        else:
            self.mic_button.setText("Mic OFF")
            glow_color = QColor(255, 64, 87, 220)
            self.mic_button.setStyleSheet(
                "QPushButton {background: #6b1018; border: 1px solid #ff4057; border-radius: 6px; color: #ffe8ec; padding: 8px 12px;}"
                "QPushButton:hover { background: #8b1621; }"
            )
        glow = QGraphicsDropShadowEffect(self.mic_button)
        glow.setBlurRadius(22)
        glow.setOffset(0, 0)
        glow.setColor(glow_color)
        self.mic_button.setGraphicsEffect(glow)

    def _update_voice_mode_button(self) -> None:
        is_premium = self.speaker.voice_mode == "premium"
        if is_premium:
            self.voice_mode_button.setText("Premium Voice")
            glow_color = QColor(255, 165, 0, 220)
            self.voice_mode_button.setStyleSheet(
                "QPushButton {"
                "background: #4a3000;"
                "border: 1px solid #ffa500;"
                "border-radius: 6px;"
                "color: #fff3d6;"
                "padding: 8px 12px;"
                "}"
                "QPushButton:hover { background: #6b4400; }"
            )
        else:
            self.voice_mode_button.setText("Standard Voice")
            glow_color = QColor(90, 120, 130, 160)
            self.voice_mode_button.setStyleSheet(
                "QPushButton {"
                "background: #17313a;"
                "border: 1px solid #446b76;"
                "border-radius: 6px;"
                "color: #e8fdff;"
                "padding: 8px 12px;"
                "}"
                "QPushButton:hover { background: #21434d; }"
            )
        glow = QGraphicsDropShadowEffect(self.voice_mode_button)
        glow.setBlurRadius(22 if is_premium else 8)
        glow.setOffset(0, 0)
        glow.setColor(glow_color)
        self.voice_mode_button.setGraphicsEffect(glow)

    def _update_object_button(self) -> None:
        enabled = self.camera.vision.object_detection_enabled
        self.object_button.setText("Disable Object Detection" if enabled else "Enable Object Detection")
        glow_color = QColor(34, 216, 255, 220) if enabled else QColor(90, 120, 130, 160)
        self.object_button.setStyleSheet(
            "QPushButton {"
            f"background: {'#0b5164' if enabled else '#17313a'};"
            f"border: 1px solid {'#22d8ff' if enabled else '#446b76'};"
            "border-radius: 6px;"
            "color: #e8fdff;"
            "padding: 8px 12px;"
            "}"
            f"QPushButton:hover {{ background: {'#0f6f87' if enabled else '#21434d'}; }}"
        )
        glow = QGraphicsDropShadowEffect(self.object_button)
        glow.setBlurRadius(22 if enabled else 8)
        glow.setOffset(0, 0)
        glow.setColor(glow_color)
        self.object_button.setGraphicsEffect(glow)

    def _style_camera_button(self, active: bool) -> None:
        glow_color = QColor(34, 216, 255, 220) if active else QColor(255, 64, 87, 210)
        self.camera_button.setStyleSheet(
            "QPushButton {"
            f"background: {'#0b5164' if active else '#6b1018'};"
            f"border: 1px solid {'#22d8ff' if active else '#ff4057'};"
            "border-radius: 6px; color: #e8fdff; padding: 8px 12px;"
            "}"
        )
        glow = QGraphicsDropShadowEffect(self.camera_button)
        glow.setBlurRadius(22)
        glow.setOffset(0, 0)
        glow.setColor(glow_color)
        self.camera_button.setGraphicsEffect(glow)

    def _position_orb(self, frame) -> None:
        face_rects = self._face_rects_for_label(frame)
        orb_size = self.ai_orb.size()
        width = self.camera_label.width()
        height = self.camera_label.height()
        margin = 18
        candidates = (
            (Qt.AlignHCenter | Qt.AlignBottom, QRect((width - orb_size.width()) // 2, height - orb_size.height() - margin, orb_size.width(), orb_size.height())),
            (Qt.AlignRight | Qt.AlignBottom, QRect(width - orb_size.width() - margin, height - orb_size.height() - margin, orb_size.width(), orb_size.height())),
            (Qt.AlignRight | Qt.AlignTop, QRect(width - orb_size.width() - margin, margin, orb_size.width(), orb_size.height())),
            (Qt.AlignLeft | Qt.AlignTop, QRect(margin, margin, orb_size.width(), orb_size.height())),
        )
        for alignment, orb_rect in candidates:
            if not any(orb_rect.intersects(face_rect.adjusted(-12, -12, 12, 12)) for face_rect in face_rects):
                self.camera_view_layout.setAlignment(self.ai_orb, alignment)
                return
        self.camera_view_layout.setAlignment(self.ai_orb, Qt.AlignRight | Qt.AlignBottom)

    def _face_rects_for_label(self, frame) -> list[QRect]:
        snapshot = self.camera.vision.snapshot()
        faces = [face for face, _, _ in snapshot.identities] or snapshot.faces
        if frame is None or not faces:
            return []
        frame_h, frame_w = frame.shape[:2]
        label_w = self.camera_label.width()
        label_h = self.camera_label.height()
        scale = min(label_w / max(1, frame_w), label_h / max(1, frame_h))
        rendered_w = frame_w * scale
        rendered_h = frame_h * scale
        x_offset = (label_w - rendered_w) / 2
        y_offset = (label_h - rendered_h) / 2
        rects = []
        for face in faces:
            rects.append(
                QRect(
                    int(x_offset + face.x * scale),
                    int(y_offset + face.y * scale),
                    int(face.w * scale),
                    int(face.h * scale),
                )
            )
        return rects

    def _run_startup_diagnostics(self) -> None:
        time.sleep(1.0)
        checks = {
            "Ollama online": self.brain.model is not None,
            f"TTS online ({self.speaker.active_engine_name})": True,
            "Webcam online": self.camera.latest_frame() is not None,
            "YOLO module": importlib.util.find_spec("ultralytics") is not None,
            "Voice recognition": importlib.util.find_spec("vosk") is not None and importlib.util.find_spec("pyaudio") is not None,
            "Face recognition": importlib.util.find_spec("onnxruntime") is not None,
            "Automation modules": importlib.util.find_spec("pycaw") is not None,
        }
        for name, ok in checks.items():
            self.append_log.emit(("OK " if ok else "MISSING ") + name)

    @staticmethod
    def _style_indicator(label: QLabel, text: str, active: bool) -> None:
        label.setText(text)
        if active:
            label.setStyleSheet("color: #d7fbff; border: 1px solid #22d8ff; border-radius: 5px; padding: 3px; background: rgba(8, 65, 80, 150);")
        else:
            label.setStyleSheet("color: #8fb6bf; border: 1px solid #355761; border-radius: 5px; padding: 3px; background: rgba(5, 20, 25, 130);")

    def closeEvent(self, event) -> None:  # noqa: N802
        self._command_stop.set()
        self.listener.stop()
        if self._command_thread.is_alive():
            self._command_thread.join(timeout=2)
        self.camera.stop()
        self.speaker.close()
        event.accept()


def run_app() -> int:
    app = QApplication([])
    window = MainWindow()
    window.show()
    return app.exec_()
