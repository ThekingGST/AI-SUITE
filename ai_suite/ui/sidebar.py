from PyQt5.QtCore import QSize, Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QIcon, QPainter, QColor, QPainterPath
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QPushButton, QWidget, QSizePolicy
from shared.config.resource_manager import ResourceManager
import os

class SidebarButton(QPushButton):
    """An icon-only button for the sidebar with hover effects and active state indicator."""
    
    def __init__(self, workspace_id: str, icon_name: str, tooltip: str, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.workspace_id = workspace_id
        self.icon_name = icon_name
        self.is_active = is_active
        
        self.setToolTip(tooltip)
        self.setFixedSize(50, 50)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        assets_dir = ResourceManager.get_icons_dir()
        icon_path = str(assets_dir / f"{icon_name}.svg")
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(24, 24))
        
        self.update_style()
        
    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()
        
    def update_style(self):
        # We use stylesheet for hover background and active border
        bg_color = "rgba(255, 255, 255, 0.05)" if self.is_active else "transparent"
        border_left = "3px solid #22d8ff" if self.is_active else "3px solid transparent"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-left: {border_left};
                border-radius: 0px;
                padding-right: 3px; /* Offset the left border to keep icon centered */
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)

class Sidebar(QFrame):
    """The professional icon-only sidebar."""
    
    tab_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(70)
        
        # Style the sidebar itself (dark background, subtle right border)
        self.setStyleSheet("""
            QFrame#sidebar {
                background-color: #04090b;
                border-right: 1px solid rgba(34, 216, 255, 0.15);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        self.buttons = {}
        
        self.add_button("jarvis", "robot", "JARVIS Workspace")
        self.add_button("friday", "code", "FRIDAY IDE")
        self.add_button("edith", "edith", "EDITH Research")
        
        layout.addStretch()
        
        # Settings at the bottom
        self.btn_settings = SidebarButton("settings", "settings", "Settings")
        self.btn_settings.clicked.connect(lambda: self._on_tab_clicked("settings"))
        self.buttons["settings"] = self.btn_settings
        layout.addWidget(self.btn_settings)
        
        # Set default active
        self.set_active_tab("jarvis")

    def add_button(self, id: str, icon_name: str, tooltip: str):
        btn = SidebarButton(id, icon_name, tooltip)
        btn.clicked.connect(lambda checked, tid=id: self._on_tab_clicked(tid))
        self.buttons[id] = btn
        self.layout().insertWidget(self.layout().count() - 1, btn)
        
    def _on_tab_clicked(self, tab_id: str):
        self.set_active_tab(tab_id)
        self.tab_clicked.emit(tab_id)
        
    def set_active_tab(self, tab_id: str):
        for tid, btn in self.buttons.items():
            btn.set_active(tid == tab_id)
