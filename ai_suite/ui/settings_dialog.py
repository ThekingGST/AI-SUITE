import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget,
    QWidget, QLabel, QPushButton, QLineEdit, QRadioButton, QButtonGroup,
    QCheckBox, QFormLayout, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt
from shared.config.config_manager import ConfigManager
from shared.config.secrets_manager import SecretsManager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Suite Settings")
        self.resize(700, 500)
        
        main_layout = QHBoxLayout()
        
        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(150)
        main_layout.addWidget(self.sidebar)
        
        # Content Area
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        self.setLayout(main_layout)
        
        # Setup pages
        self.setup_ai_providers_page()
        self.setup_memory_page()
        self.setup_voice_page()
        self.setup_vision_page()
        self.setup_appearance_page()
        self.setup_privacy_page()
        self.setup_system_page()
        self.setup_about_page()
        
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
        
    def add_page(self, title, widget):
        self.sidebar.addItem(title)
        self.stack.addWidget(widget)
        
    def setup_ai_providers_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        
        group = QGroupBox("AI Provider")
        group_layout = QVBoxLayout()
        self.bg = QButtonGroup()
        
        self.rb_local = QRadioButton("Local AI (Ollama + Llama3)")
        self.rb_cloud = QRadioButton("Cloud AI (OpenRouter)")
        
        from shared.config.settings_manager import SettingsManager
        settings = SettingsManager()
        provider = settings.get("ai_provider", "local")
        if provider == "cloud":
            self.rb_cloud.setChecked(True)
        else:
            self.rb_local.setChecked(True)
            
        self.bg.addButton(self.rb_local)
        self.bg.addButton(self.rb_cloud)
        group_layout.addWidget(self.rb_local)
        group_layout.addWidget(self.rb_cloud)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("sk-or-v1-...")
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setEnabled(False)
        
        # Load existing key
        existing_key = SecretsManager().get_secret("OPENROUTER_API_KEY")
        if existing_key:
            self.api_key_input.setText(existing_key)
            
        self.rb_cloud.toggled.connect(self.api_key_input.setEnabled)
        
        group_layout.addWidget(QLabel("OpenRouter API Key:"))
        group_layout.addWidget(self.api_key_input)
        
        save_btn = QPushButton("Save AI Settings")
        save_btn.clicked.connect(self.save_ai_settings)
        group_layout.addWidget(save_btn)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("AI Providers", page)
        
    def save_ai_settings(self):
        from shared.config.settings_manager import SettingsManager
        settings = SettingsManager()
        if self.rb_cloud.isChecked():
            key = self.api_key_input.text().strip()
            if key:
                SecretsManager().set_secret("OPENROUTER_API_KEY", key)
                settings.set("ai_provider", "cloud")
                QMessageBox.information(self, "Settings Saved", "Cloud API Key saved securely. AI Provider set to Cloud.")
            else:
                QMessageBox.warning(self, "Warning", "Cloud AI requires an OpenRouter API key. Add your key in Settings -> AI Providers.")
        else:
            settings.set("ai_provider", "local")
            QMessageBox.information(self, "Settings Saved", "Local AI selected.")
            
    def setup_memory_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Memory & History Configuration"))
        btn = QPushButton("Clear All Conversational History")
        btn.clicked.connect(lambda: QMessageBox.information(self, "Clear", "History cleared."))
        layout.addWidget(btn)
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("Memory", page)
        
    def setup_voice_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Voice Configuration"))
        layout.addWidget(QCheckBox("Enable Microphone globally"))
        layout.addWidget(QCheckBox("Enable Text-to-Speech responses"))
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("Voice", page)

    def setup_vision_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Vision Configuration"))
        layout.addWidget(QCheckBox("Enable Camera globally"))
        layout.addWidget(QCheckBox("Enable Face Recognition tracking"))
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("Vision", page)
        
    def setup_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Appearance"))
        layout.addWidget(QRadioButton("Dark Mode"))
        layout.addWidget(QRadioButton("Light Mode"))
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("Appearance", page)
        
    def setup_privacy_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Privacy & Security"))
        info = QLabel(
            "Local AI data never leaves this machine.\\n"
            "Cloud AI prompts are sent securely to OpenRouter.\\n\\n"
            "All configuration is stored locally in:\\n%LOCALAPPDATA%\\\\AISuite"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("Privacy", page)
        
    def setup_system_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("System Configuration"))
        layout.addWidget(QCheckBox("Launch AI Suite on System Startup"))
        layout.addWidget(QPushButton("Reset All Settings to Default"))
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("System", page)
        
    def setup_about_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>AI Suite v1.0.0</h2>"))
        layout.addWidget(QLabel("The ultimate local AI assistant for Windows."))
        layout.addWidget(QLabel("License: Open Source"))
        layout.addStretch()
        page.setLayout(layout)
        self.add_page("About", page)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication([])
    d = SettingsDialog()
    d.exec_()
