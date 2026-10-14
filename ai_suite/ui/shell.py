from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect
)
from PyQt5.QtGui import QFont, QCursor, QColor
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty

from ai_suite.ui.sidebar import Sidebar
from jarvis_ai.utils.logger import LOGGER

import platform
import getpass
import os

def _get_current_user_name() -> str:
    if platform.system() == "Windows":
        try:
            import ctypes
            GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
            size = ctypes.c_ulong(1024)
            buf = ctypes.create_unicode_buffer(1024)
            if GetUserNameEx(3, buf, ctypes.byref(size)):
                name = buf.value
                return name.split(" ")[0] if " " in name else name
        except Exception:
            pass
    try:
        return getpass.getuser()
    except Exception:
        return "User"

def _get_compute_info() -> str:
    try:
        from shared.hardware.manager import HardwareManager
        hw = HardwareManager()
        if not getattr(hw, "_initialized", False):
            hw.detect_all()
        if hw.gpu.available:
            name = hw.gpu.name
            if "RTX" in name:
                return "RTX " + name.split("RTX ")[1].split(" ")[0]
            elif "GTX" in name:
                return "GTX " + name.split("GTX ")[1].split(" ")[0]
            return "NVIDIA GPU"
        return "CPU mode"
    except Exception:
        return "CPU mode"


class TopBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(50)
        self.setStyleSheet("""
            TopBar {
                background: #0D1117;
                border-bottom: 1px solid #21262D;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.title_label = QLabel("AI SUITE //")
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.title_label.setStyleSheet("color: #8b9fb0; letter-spacing: 1px;")
        layout.addWidget(self.title_label)
        
        self.workspace_label = QLabel("JARVIS")
        self.workspace_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.workspace_label.setStyleSheet("color: #ffffff; letter-spacing: 1px;")
        layout.addWidget(self.workspace_label)
        
        layout.addStretch(1)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search • Run • Open • Diagnose... (Ctrl+K)")
        self.search_box.setMinimumWidth(150)
        self.search_box.setMaximumWidth(400)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px 12px;
                color: #c9d1d9;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
                background: #0D1117;
            }
        """)
        layout.addWidget(self.search_box)
        
        layout.addStretch(1)
        
        # Helper to create chips
        def create_chip(text: str, text_color: str, bg_color: str, border_color: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {text_color}; font-size: 12px; font-weight: bold; background: {bg_color}; padding: 4px 8px; border-radius: 4px; border: 1px solid {border_color};")
            # This allows the layout to shrink if space is tight, gracefully collapsing without breaking layout
            lbl.setSizePolicy(lbl.sizePolicy().Policy.Minimum, lbl.sizePolicy().Policy.Fixed)
            return lbl

        # Model Chip
        self.model_chip = create_chip("🧠 Llama 3", "#8b9fb0", "#161B22", "#30363D")
        layout.addWidget(self.model_chip)
        layout.addSpacing(6)
        
        # Voice Chip
        self.voice_chip = create_chip("🎤 Edge-TTS", "#8b9fb0", "#161B22", "#30363D")
        layout.addWidget(self.voice_chip)
        layout.addSpacing(6)
        
        # Compute Chip
        compute_text = _get_compute_info()
        self.compute_chip = create_chip(f"⚡ {compute_text}", "#34D399", "rgba(52, 211, 153, 0.1)", "rgba(52, 211, 153, 0.3)")
        layout.addWidget(self.compute_chip)
        layout.addSpacing(6)
        
        # User Chip
        user_name = _get_current_user_name()
        self.user_chip = create_chip(f"👤 {user_name}", "#38BDF8", "rgba(56, 189, 248, 0.1)", "rgba(56, 189, 248, 0.3)")
        layout.addWidget(self.user_chip)
        
    def set_workspace_title(self, title: str):
        self.workspace_label.setText(title.upper())

class StatusBar(QWidget):
    def __init__(self):
        super().__init__()
        self.event_bus = None
        self.setFixedHeight(32)
        self.setStyleSheet("""
            StatusBar {
                background: #010409;
                border-top: 1px solid #21262D;
            }
            QLabel {
                color: #8b9fb0;
                font-size: 11px;
                font-family: "Cascadia Code", "Consolas", monospace;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(20)
        
        self.mode_label = QLabel("MODE: OFFLINE")
        layout.addWidget(self.mode_label)
        
        self.status_label = QLabel("SYSTEMS ONLINE")
        self.status_label.setStyleSheet("color: #38BDF8;")
        layout.addWidget(self.status_label)
        
        layout.addStretch(1)
        
        self.mic_label = QLabel("MIC: ON")
        self.mic_label.setStyleSheet("color: #34D399;")
        layout.addWidget(self.mic_label)
        
        self.cam_label = QLabel("CAM: ON")
        self.cam_label.setStyleSheet("color: #34D399;")
        layout.addWidget(self.cam_label)
        
        layout.addSpacing(10)
        
        self.fps_label = QLabel("FPS: 30")
        layout.addWidget(self.fps_label)
        
        self.latency_label = QLabel("LAT: 12ms")
        layout.addWidget(self.latency_label)
        
        layout.addSpacing(10)
        
        self.cpu_label = QLabel("CPU: 0%")
        layout.addWidget(self.cpu_label)
        
        self.ram_label = QLabel("RAM: 0%")
        layout.addWidget(self.ram_label)
        
        self.gpu_util_label = QLabel("VRAM: 0%")
        layout.addWidget(self.gpu_util_label)
        
        # Metrics timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_metrics)
        self._timer.start(2000)
        
    def inject_services(self, event_bus):
        self.event_bus = event_bus
        self.event_bus.assistantStateChanged.connect(self._on_assistant_state)
        
    def _update_metrics(self):
        from ai_suite.core.registry import ServiceContainer
        from ai_suite.intelligence import IntelligenceService
        
        intel = ServiceContainer.get(IntelligenceService)
        if intel:
            cpu_report = intel.inspect("cpu")
            ram_report = intel.inspect("memory")
            
            cpu = cpu_report.metrics.get("usage_percent", 0.0)
            ram = ram_report.metrics.get("usage_percent", 0.0)
            
            self.cpu_label.setText(f"CPU: {cpu}%")
            self.ram_label.setText(f"RAM: {ram}%")
            
            try:
                from shared.hardware.manager import HardwareManager
                vram_usage = HardwareManager().get_vram_usage()
                vram_pct = vram_usage.get("percent", 0.0)
                if HardwareManager().get_gpu_info().available:
                    self.gpu_util_label.setText(f"VRAM: {vram_pct:.1f}%")
                else:
                    self.gpu_util_label.setText("VRAM: N/A")
            except Exception:
                self.gpu_util_label.setText("VRAM: N/A")
        
    def _on_assistant_state(self, id: str, old: str, new: str):
        self.mode_label.setText(f"{id.upper()}: {new.upper()}")


class FadeOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._alpha = 0
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def getAlpha(self):
        return self._alpha

    def setAlpha(self, value):
        self._alpha = value
        self.update()

    alpha = pyqtProperty(int, getAlpha, setAlpha)

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor
        painter = QPainter(self)
        if not painter.isActive():
            return
        painter.fillRect(self.rect(), QColor(13, 17, 23, self._alpha))


class FadingStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QStackedWidget { background-color: #0D1117; }")
        self.overlay = FadeOverlay(self)
        self.overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())

    def setCurrentIndex(self, index):
        if index == self.currentIndex():
            return
            
        current_widget = self.currentWidget()
        
        if current_widget:
            self.overlay.raise_()
            self.overlay.show()
            
            self.anim_out = QPropertyAnimation(self.overlay, b"alpha")
            self.anim_out.setDuration(150)
            self.anim_out.setStartValue(0)
            self.anim_out.setEndValue(255)
            self.anim_out.setEasingCurve(QEasingCurve.InOutQuad)
            
            def on_fade_out():
                super(FadingStackedWidget, self).setCurrentIndex(index)
                
                self.anim_in = QPropertyAnimation(self.overlay, b"alpha")
                self.anim_in.setDuration(150)
                self.anim_in.setStartValue(255)
                self.anim_in.setEndValue(0)
                self.anim_in.setEasingCurve(QEasingCurve.InOutQuad)
                
                def on_fade_in():
                    self.overlay.hide()
                    
                self.anim_in.finished.connect(on_fade_in)
                self.anim_in.start()
                
            self.anim_out.finished.connect(on_fade_out)
            self.anim_out.start()
        else:
            super().setCurrentIndex(index)

class AISuiteWindow(QMainWindow):
    """The premium master shell that hosts all AI Workspaces."""

    def __init__(self, boot_mode=False) -> None:
        super().__init__()
        self.assistant_manager = None
        self.session_manager = None
        self.workspace_manager = None
        self.event_bus = None
        
        self.setWindowTitle("AI Suite")
        self.resize(1440, 900)
        
        # Global dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0D1117;
            }
            QWidget#true_central {
                background-color: #0D1117;
            }
        """)

        self.create_shell()
        
        if boot_mode:
            self.show_overlay()
            
    def create_shell(self) -> None:
        true_central = QWidget()
        true_central.setObjectName("true_central")
        self.setCentralWidget(true_central)
        
        # We use a StackAll layout so the overlay can sit on top of the dashboard
        from PyQt5.QtWidgets import QStackedLayout
        self.root_layout = QStackedLayout(true_central)
        self.root_layout.setStackingMode(QStackedLayout.StackAll)
        
        # 1. Dashboard Layer
        self.dashboard_container = QWidget()
        
        # Main vertical layout (TopBar + Middle + StatusBar)
        dashboard_vbox = QVBoxLayout(self.dashboard_container)
        dashboard_vbox.setContentsMargins(0, 0, 0, 0)
        dashboard_vbox.setSpacing(0)
        
        self.top_bar = TopBar()
        dashboard_vbox.addWidget(self.top_bar)
        
        # Middle horizontal layout (Sidebar + Stack)
        middle_widget = QWidget()
        middle_hbox = QHBoxLayout(middle_widget)
        middle_hbox.setContentsMargins(0, 0, 0, 0)
        middle_hbox.setSpacing(0)
        
        self.sidebar = Sidebar()
        middle_hbox.addWidget(self.sidebar)
        
        self.stack = FadingStackedWidget()
        middle_hbox.addWidget(self.stack, 1)
        
        dashboard_vbox.addWidget(middle_widget, 1)
        
        self.status_bar = StatusBar()
        dashboard_vbox.addWidget(self.status_bar)
        
        self.root_layout.addWidget(self.dashboard_container)
        
    def show_overlay(self) -> None:
        # Hide the dashboard elements initially
        self.dashboard_op_effect = QGraphicsOpacityEffect(self.dashboard_container)
        self.dashboard_op_effect.setOpacity(0.0)
        self.dashboard_container.setGraphicsEffect(self.dashboard_op_effect)
        
        # Instantiate overlay
        from ai_suite.ui.boot.boot_overlay import BootOverlay
        self.boot_overlay = BootOverlay()
        self.boot_overlay.transition_complete.connect(self.boot_complete)
        self.root_layout.addWidget(self.boot_overlay)

    def inject_services(self, assistant_manager, session_manager, workspace_manager, event_bus) -> None:
        self.assistant_manager = assistant_manager
        self.session_manager = session_manager
        self.workspace_manager = workspace_manager
        self.event_bus = event_bus
        
        # Inject event bus into status bar
        self.status_bar.inject_services(event_bus)
        
        self.initialize_dashboard()
        
    def initialize_dashboard(self) -> None:
        # Give the UI container to the WorkspaceCoordinator
        self.workspace_manager.set_container(self.stack)
        
        # Connect signals
        self.sidebar.tab_clicked.connect(self._on_tab_clicked)
        
    def reveal_dashboard(self) -> None:
        # 1. Remove the dashboard opacity effect entirely
        # Keeping it attached, even at 1.0 opacity, forces the entire application 
        # to render through a QWidgetEffectSourcePrivate pixmap, breaking active painters.
        self.dashboard_container.setGraphicsEffect(None)
        
        self._reveal_effects = []
        self._reveal_anims = []
        
        # Order: Header -> Sidebar -> Workspace (Stack) -> Status indicators
        widgets = [self.top_bar, self.sidebar, self.stack, self.status_bar]
        
        for i, widget in enumerate(widgets):
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(0.0)
            widget.setGraphicsEffect(effect)
            self._reveal_effects.append(effect)
            
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(400)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.InOutQuad)
            
            # Remove the graphics effect entirely after the animation finishes
            # Leaving it permanently attached causes QWidgetEffectSourcePrivate pixmap collisions 
            # with actively painting children (like HologramCore).
            anim.finished.connect(lambda w=widget: w.setGraphicsEffect(None))
            
            # Stagger the animations
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(i * 150, anim.start)
            
            self._reveal_anims.append(anim)
        
    def boot_complete(self) -> None:
        # Cleanup overlay
        if hasattr(self, 'boot_overlay') and self.boot_overlay:
            self.root_layout.removeWidget(self.boot_overlay)
            self.boot_overlay.deleteLater()
            self.boot_overlay = None
        
    def _on_tab_clicked(self, workspace_id: str) -> None:
        if workspace_id == "settings":
            from ai_suite.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog(self)
            dialog.exec_()
            # Do not switch workspaces or titles
            return
            
        self.top_bar.set_workspace_title(workspace_id)
        LOGGER.info(f"Sidebar requested workspace: {workspace_id}")
        self.workspace_manager.activate_workspace(workspace_id)

    def closeEvent(self, event) -> None:
        LOGGER.info("Initiating AI Suite shutdown...")
        if self.workspace_manager:
            try:
                self.workspace_manager.shutdown_all()
            except Exception as e:
                LOGGER.error(f"Error during workspace shutdown: {e}")
        event.accept()