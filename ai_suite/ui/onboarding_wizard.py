import os
import sys
import shutil
import subprocess
import urllib.request
import tempfile
import json
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QLabel, QCheckBox, 
    QTextBrowser, QRadioButton, QButtonGroup, QLineEdit, 
    QProgressBar, QMessageBox, QPushButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from shared.config.config_manager import ConfigManager
from shared.config.secrets_manager import SecretsManager

LOG = logging.getLogger("OnboardingWizard")
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# ------------------------------------------------------------------------------
# Workers
# ------------------------------------------------------------------------------
class HealthCheckWorker(QThread):
    progress = pyqtSignal(int, str, bool)
    finished = pyqtSignal(bool, dict)

    def run(self):
        passed = True
        status_flags = {
            "camera": False,
            "yolo": False,
            "sface": False,
            "voice": False,
            "tts": False,
            "ollama": False,
            "python": False
        }
        
        # 1. Camera
        self.progress.emit(10, "Checking Camera...", True)
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    self.progress.emit(15, "Camera - Ready", True)
                    status_flags["camera"] = True
                else:
                    self.progress.emit(15, "Camera - Failed to read frame", False)
            else:
                self.progress.emit(15, "Camera - Not detected (Vision features limited)", False)
        except Exception as e:
            self.progress.emit(15, f"Camera error: {e}", False)
            
        # Check Registered Models
        self.progress.emit(18, "Checking Registered Models...", True)
        try:
            from shared.models.model_registry import ModelRegistry
            registry = ModelRegistry()
            missing_req = []
            missing_opt = []
            for name, info in registry.get_all().items():
                path = registry.get_model_path(name)
                if not path or not path.exists():
                    if info.required:
                        missing_req.append(name)
                    else:
                        missing_opt.append(name)
            
            if missing_opt:
                self.progress.emit(19, f"Missing optional models: {', '.join(missing_opt)}", True)
                
            if missing_req:
                self.progress.emit(20, f"Missing REQUIRED models: {', '.join(missing_req)}", False)
                passed = False
            else:
                self.progress.emit(20, "Required models found", True)
        except Exception as e:
            self.progress.emit(20, f"Model registry error: {e}", False)
            
        # 2. YOLO
        self.progress.emit(25, "Initializing YOLO Object Detection...", True)
        try:
            from jarvis_ai.core.model_manager import ModelManager
            manager = ModelManager()
            yolo = manager.get_yolo()
            if yolo:
                # Lightweight inference test if we got a frame
                if 'frame' in locals() and status_flags["camera"]:
                    results = yolo(frame, verbose=False)
                self.progress.emit(35, "Object Detection (YOLO) - Ready", True)
                status_flags["yolo"] = True
            else:
                self.progress.emit(35, "Object Detection (YOLO) - Failed to load", False)
                passed = False
        except Exception as e:
            self.progress.emit(35, f"YOLO error: {e}", False)
            passed = False
            
        # 3. SFace
        self.progress.emit(45, "Initializing Face Recognition...", True)
        try:
            from jarvis_ai.core.model_manager import ModelManager
            manager = ModelManager()
            sface, _ = manager.get_sface_session()
            face_detector = manager.get_yunet_detector()
            if sface and face_detector:
                self.progress.emit(55, "Face Recognition - Ready", True)
                status_flags["sface"] = True
            else:
                self.progress.emit(55, "Face Recognition - Failed to load", False)
                passed = False
        except Exception as e:
            self.progress.emit(55, f"Face Recognition error: {e}", False)
            passed = False

        # 4. Voice (STT)
        self.progress.emit(60, "Initializing Voice Recognition...", True)
        try:
            from jarvis_ai.voice.input.stt.vosk_backend import VoskBackend
            from jarvis_ai.voice.input.profile import AudioProfile
            profile = AudioProfile(name="test")
            stt = VoskBackend(profile)
            self.progress.emit(65, "Voice Recognition - Ready", True)
            status_flags["voice"] = True
        except Exception as e:
            self.progress.emit(65, f"Voice Recognition error: {e}", False)
            passed = False

        # 5. TTS
        self.progress.emit(70, "Initializing Edge-TTS...", True)
        try:
            # We just test the import as edge-tts is command line based
            import edge_tts
            self.progress.emit(75, "Text-to-Speech - Ready", True)
            status_flags["tts"] = True
        except Exception as e:
            self.progress.emit(75, f"TTS error: {e}", False)
            passed = False
            
        # 6. Ollama CLI & Connection
        self.progress.emit(80, "Checking Ollama Engine...", True)
        if shutil.which("ollama"):
            try:
                import urllib.request
                req = urllib.request.Request("http://127.0.0.1:11434/api/version")
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        self.progress.emit(85, "Ollama Engine - Ready", True)
                        status_flags["ollama"] = True
                    else:
                        self.progress.emit(85, "Ollama Engine - Service not responding properly", False)
            except Exception:
                # Exists but maybe service not started
                self.progress.emit(85, "Ollama Engine - Installed but service not running", False)
        else:
            self.progress.emit(85, "Ollama Engine - Not Found (Required for Local AI)", False)
            
        # 7. Python (for FRIDAY)
        self.progress.emit(90, "Checking Python runtime (for FRIDAY)...", True)
        if shutil.which("python") or shutil.which("py"):
            self.progress.emit(100, "Python Runtime - Ready", True)
            status_flags["python"] = True
        else:
            self.progress.emit(100, "Python Runtime - Not Found (Required for FRIDAY virtual environments)", False)

        self.finished.emit(passed, status_flags)

class DependencyAutomationWorker(QThread):
    progress = pyqtSignal(str, bool)
    finished = pyqtSignal(bool, dict)

    def __init__(self, status_flags):
        super().__init__()
        self.status_flags = status_flags

    def run(self):
        passed = True
        
        # 1. Python
        if not self.status_flags.get("python", False):
            self.progress.emit("Downloading Python runtime for FRIDAY...", True)
            try:
                temp_dir = tempfile.gettempdir()
                installer_path = os.path.join(temp_dir, "python-3.11.9-amd64.exe")
                
                urllib.request.urlretrieve("https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe", installer_path)
                self.progress.emit("Download complete. Installing silently for current user...", True)
                
                result = subprocess.run([installer_path, "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0"], capture_output=True, creationflags=CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    # Verify python is available
                    import time
                    python_ready = False
                    for _ in range(5):
                        time.sleep(1)
                        if shutil.which("python") or shutil.which("py"):
                            python_ready = True
                            break
                    if python_ready:
                        self.progress.emit("Python installed and verified successfully.", True)
                        self.status_flags["python"] = True
                    else:
                        self.progress.emit("Python installer finished, but python is still not in PATH.", False)
                        passed = False
                else:
                    self.progress.emit("Python installation failed.", False)
                    passed = False
            except Exception as e:
                self.progress.emit(f"Python Installation error: {e}", False)
                passed = False

        # 2. Ollama
        if not self.status_flags.get("ollama", False):
            self.progress.emit("Downloading official Ollama installer to %TEMP%...", True)
            try:
                temp_dir = tempfile.gettempdir()
                installer_path = os.path.join(temp_dir, "OllamaSetup.exe")
                
                urllib.request.urlretrieve("https://ollama.com/download/OllamaSetup.exe", installer_path)
                self.progress.emit("Download complete. Installing silently (this may take a minute)...", True)
                
                result = subprocess.run([installer_path, "/SILENT"], capture_output=True, creationflags=CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    self.progress.emit("Ollama installed successfully. Verifying service...", True)
                    import time
                    ollama_ready = False
                    for _ in range(10):
                        time.sleep(2)
                        try:
                            req = urllib.request.Request("http://127.0.0.1:11434/api/version")
                            with urllib.request.urlopen(req, timeout=2) as response:
                                if response.status == 200:
                                    ollama_ready = True
                                    break
                        except Exception:
                            pass
                    if ollama_ready:
                        self.progress.emit("Ollama service verified and running.", True)
                        self.status_flags["ollama"] = True
                    else:
                        self.progress.emit("Ollama installed but service is not reachable.", False)
                        passed = False
                else:
                    self.progress.emit("Ollama installation failed (installer returned non-zero).", False)
                    passed = False
            except Exception as e:
                self.progress.emit(f"Ollama Installation error: {e}", False)
                passed = False

        self.finished.emit(passed, self.status_flags)


class OllamaPullWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def run(self):
        self.progress.emit("Starting download of llama3 (this may take a while)...")
        try:
            process = subprocess.Popen(
                ["ollama", "pull", "llama3"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=CREATE_NO_WINDOW
            )
            for line in process.stdout:
                if line:
                    self.progress.emit(line.strip())
            process.wait()
            
            if process.returncode == 0:
                self.progress.emit("Verifying llama3 functionality...")
                # Functional test
                req = urllib.request.Request(
                    "http://127.0.0.1:11434/api/generate",
                    data=json.dumps({"model": "llama3", "prompt": "Hi", "stream": False}).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        self.finished.emit(True)
                    else:
                        self.finished.emit(False)
            else:
                self.finished.emit(False)
        except Exception as e:
            self.progress.emit(f"Failed to pull/verify llama3: {e}")
            self.finished.emit(False)

# ------------------------------------------------------------------------------
# Wizard Pages
# ------------------------------------------------------------------------------
class WelcomePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Welcome to AI Suite")
        self.setSubTitle("Setup your ultimate local AI assistant.")
        
        layout = QVBoxLayout()
        label = QLabel(
            "Welcome to the AI Suite Onboarding.\n\n"
            "This wizard will automatically verify your system health, prepare your AI "
            "engines, and configure your preferred backend (Local or Cloud)."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)

class LicensePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Legal & Privacy")
        self.setSubTitle("Please review the privacy policy before continuing.")
        
        layout = QVBoxLayout()
        
        self.browser = QTextBrowser()
        self.browser.setPlainText(
            "AI Suite Privacy Policy & EULA\n\n"
            "LOCAL AI (OLLAMA):\n"
            "If you select Local AI, all processing occurs locally on your machine. No prompts or data are sent externally.\n\n"
            "CLOUD AI (OPENROUTER):\n"
            "If you select Cloud AI, your prompts will be sent to the selected cloud provider API for processing.\n\n"
            "By using this software, you agree to these terms and conditions. Press 'I Accept' to continue."
        )
        layout.addWidget(self.browser)
        
        self.accept_check = QCheckBox("I accept the terms and conditions")
        self.registerField("license_accepted*", self.accept_check)
        layout.addWidget(self.accept_check)
        
        self.setLayout(layout)

class HealthCheckPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("System Health Check")
        self.setSubTitle("Verifying hardware and model dependencies...")
        
        layout = QVBoxLayout()
        
        self.log_browser = QTextBrowser()
        layout.addWidget(self.log_browser)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        self.worker = None
        self.is_complete = False

    def initializePage(self):
        self.log_browser.clear()
        self.progress_bar.setValue(0)
        self.is_complete = False
        self.completeChanged.emit()
        
        self.worker = HealthCheckWorker()
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, value, message, ok):
        self.progress_bar.setValue(value)
        color = "green" if ok else "red"
        self.log_browser.append(f"<span style='color:{color};'>{message}</span>")

    def on_finished(self, passed, status_flags):
        # We store status_flags so the next page knows what's missing
        self.wizard().status_flags = status_flags
        self.is_complete = True
        self.completeChanged.emit()

    def isComplete(self):
        return self.is_complete

class DependencyPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Required Components")
        self.setSubTitle("Installing missing dependencies automatically.")
        
        self.layout = QVBoxLayout()
        
        self.label = QLabel("Analyzing requirements...")
        self.layout.addWidget(self.label)
        
        self.log_browser = QTextBrowser()
        self.layout.addWidget(self.log_browser)
        
        self.setLayout(self.layout)
        self.is_complete = False
        self.worker = None

    def initializePage(self):
        flags = getattr(self.wizard(), "status_flags", {})
        
        needs_ollama = not flags.get("ollama", False)
        needs_python = not flags.get("python", False)
        
        if not needs_ollama and not needs_python:
            self.label.setText("All dependencies are already installed!")
            self.log_browser.append("<span style='color:green;'>? Python is ready</span>")
            self.log_browser.append("<span style='color:green;'>? Ollama is ready</span>")
            self.is_complete = True
            self.completeChanged.emit()
            return
            
        self.is_complete = False
        self.completeChanged.emit()
        
        self.label.setText("Installing missing components...")
        self.worker = DependencyAutomationWorker(flags)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, message, ok):
        color = "green" if ok else "red"
        # If it's just an info message (like "Downloading..."), we can use black, but the signal passes bool.
        # Let's map ok=True to green, ok=False to red. Wait, some messages are just info. 
        # I'll just use normal color for True and red for False unless it says 'successfully', but for now green is fine.
        if ok and "Downloading" in message:
            color = "black"
        self.log_browser.append(f"<span style='color:{color};'>{message}</span>")

    def on_finished(self, passed, status_flags):
        self.wizard().status_flags = status_flags
        if passed:
            self.label.setText("All required components are ready.")
            self.is_complete = True
        else:
            self.label.setText("Some dependencies failed to install. Please check logs.")
            self.is_complete = False # Require manual intervention or retry
        self.completeChanged.emit()

    def isComplete(self):
        return self.is_complete


class BackendPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("AI Backend Configuration")
        self.setSubTitle("Choose whether you want to run AI locally or via the cloud.")
        
        layout = QVBoxLayout()
        self.group = QButtonGroup()
        
        self.radio_local = QRadioButton("Local AI (Ollama + Llama3)")
        self.radio_local.setChecked(True)
        self.group.addButton(self.radio_local)
        layout.addWidget(self.radio_local)
        
        label_local = QLabel("100% private processing. Requires a capable machine.")
        label_local.setStyleSheet("color: gray;")
        layout.addWidget(label_local)
        
        self.radio_cloud = QRadioButton("Cloud AI (OpenRouter)")
        self.group.addButton(self.radio_cloud)
        layout.addWidget(self.radio_cloud)
        
        label_cloud = QLabel("Requires internet and an OpenRouter API Key. Faster on weak hardware.")
        label_cloud.setStyleSheet("color: gray;")
        layout.addWidget(label_cloud)
        
        self.registerField("backend_local", self.radio_local)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-or-v1-...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setEnabled(False)
        layout.addWidget(QLabel("\nOpenRouter API Key (Required for Cloud):"))
        layout.addWidget(self.api_key_input)
        
        self.radio_cloud.toggled.connect(self.api_key_input.setEnabled)
        self.api_key_input.textChanged.connect(self.completeChanged)
        self.setLayout(layout)

    def isComplete(self):
        if self.radio_cloud.isChecked() and not self.api_key_input.text().strip():
            return False
        return True

class LocalSetupPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Local AI Setup")
        self.setSubTitle("Preparing Ollama and Llama3 for local execution.")
        
        layout = QVBoxLayout()
        self.label = QLabel("Checking Llama3 model...")
        layout.addWidget(self.label)
        
        self.log_browser = QTextBrowser()
        layout.addWidget(self.log_browser)
        
        self.setLayout(layout)
        self.worker = None
        self.is_complete = False

    def initializePage(self):
        if not self.field("backend_local"):
            self.is_complete = True
            self.completeChanged.emit()
            return
            
        self.is_complete = False
        self.completeChanged.emit()
        self.log_browser.clear()
        
        # Check if llama3 is already pulled
        try:
            req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode())
                models = [m["name"] for m in data.get("models", [])]
                if any("llama3" in m for m in models):
                    self.label.setText("Llama3 is already installed and verified!")
                    self.is_complete = True
                    self.completeChanged.emit()
                    return
        except Exception:
            pass

        self.label.setText("Pulling Llama3 model automatically...")
        self.worker = OllamaPullWorker()
        self.worker.progress.connect(self.log_browser.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success):
        self.is_complete = True
        if success:
            self.log_browser.append("\n<span style='color:green;'>Llama3 is ready! Functional test passed.</span>")
        else:
            self.log_browser.append("\n<span style='color:red;'>Failed to pull Llama3. You can pull it later via Settings.</span>")
        self.completeChanged.emit()

    def isComplete(self):
        if not self.field("backend_local"):
            return True
        return self.is_complete

class FinishPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("All Set!")
        self.setSubTitle("AI Suite is ready to launch.")
        
        layout = QVBoxLayout()
        label = QLabel(
            "Configuration complete.\n\n"
            "JARVIS and FRIDAY are now ready to assist you. "
            "You can change these settings at any time in the Settings menu."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setLayout(layout)

# ------------------------------------------------------------------------------
# Wizard Core
# ------------------------------------------------------------------------------
class OnboardingWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Suite Setup")
        self.resize(650, 500)
        self.setWizardStyle(QWizard.ModernStyle)
        
        self.addPage(WelcomePage())
        self.addPage(LicensePage())
        self.addPage(HealthCheckPage())
        self.addPage(DependencyPage())
        self.addPage(BackendPage())
        self.addPage(LocalSetupPage())
        self.addPage(FinishPage())

    def accept(self):
        # Save API key if provided via SecretsManager
        api_key = self.page(4).api_key_input.text().strip()  # BackendPage is index 4
        if api_key and not self.field("backend_local"):
            SecretsManager().set_secret("OPENROUTER_API_KEY", api_key)
        super().accept()

def run_onboarding(parent=None):
    wizard = OnboardingWizard(parent=parent)
    return wizard.exec_()
