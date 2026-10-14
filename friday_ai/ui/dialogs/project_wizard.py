from __future__ import annotations
import subprocess
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QCheckBox, QFileDialog, QMessageBox, QWidget,
)

from friday_ai.core.theme import THEME
from friday_ai.core.signals import signals
from friday_ai.services.project_templates import default_registry, ProjectTemplate
from shared.logger import get_logger

LOG = get_logger("friday.wizard")


class TemplateItemWidget(QWidget):
    """Custom widget to display a template in the list."""
    
    def __init__(self, template: ProjectTemplate, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_md, THEME.space_sm, THEME.space_md, THEME.space_sm)
        layout.setSpacing(THEME.space_xs)
        
        name_lbl = QLabel(template.name)
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: {THEME.font_size_base}px; color: {THEME.text_primary};")
        
        desc_lbl = QLabel(template.description)
        desc_lbl.setStyleSheet(f"color: {THEME.text_secondary}; font-size: {THEME.font_size_sm}px;")
        desc_lbl.setWordWrap(True)
        
        layout.addWidget(name_lbl)
        layout.addWidget(desc_lbl)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


class ProjectWizard(QDialog):
    """Wizard to create a new project."""
    
    def __init__(self, project_manager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project_manager = project_manager
        
        self.setWindowTitle("Create New Project")
        self.setFixedSize(700, 550)
        self.setStyleSheet(
            f"QDialog {{ background: {THEME.bg_base}; }}"
            f"QLabel {{ color: {THEME.text_primary}; }}"
        )
        
        self._templates_by_id: dict[str, ProjectTemplate] = {}
        self._build_ui()
        self._populate_templates()
        self._on_template_selected()
        
    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(THEME.space_xl, THEME.space_xl, THEME.space_xl, THEME.space_xl)
        main_layout.setSpacing(THEME.space_lg)
        
        # Title
        title = QLabel("Create New Project")
        title.setStyleSheet(f"font-size: {THEME.font_size_base + 4}px; font-weight: bold; color: {THEME.accent};")
        main_layout.addWidget(title)
        
        # Split into main content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(THEME.space_lg)
        
        # Left side: Templates list
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Templates:"))
        self._template_list = QListWidget()
        self._template_list.setStyleSheet(f"""
            QListWidget {{
                background: {THEME.bg_surface};
                border: {THEME.border_width}px solid {THEME.border_default};
                border-radius: {THEME.radius_md}px;
                outline: none;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {THEME.border_muted};
            }}
            QListWidget::item:selected {{
                background-color: {THEME.accent_muted};
            }}
        """)
        self._template_list.currentItemChanged.connect(self._on_template_selected)
        left_layout.addWidget(self._template_list)
        content_layout.addLayout(left_layout, 1)
        
        # Right side: Details
        right_layout = QVBoxLayout()
        right_layout.setSpacing(THEME.space_md)
        
        # Name
        right_layout.addWidget(QLabel("Project Name:"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Enter project name")
        # Update preview when name changes
        self._name_input.textChanged.connect(self._on_template_selected)
        right_layout.addWidget(self._name_input)
        
        # Location
        right_layout.addWidget(QLabel("Location:"))
        loc_layout = QHBoxLayout()
        loc_layout.setSpacing(THEME.space_sm)
        self._loc_input = QLineEdit()
        self._loc_input.setText(str(Path.home() / "Projects"))
        loc_layout.addWidget(self._loc_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_location)
        loc_layout.addWidget(browse_btn)
        right_layout.addLayout(loc_layout)
        
        # Preview
        right_layout.addWidget(QLabel("Preview:"))
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet(f"""
            QTextEdit {{
                background: {THEME.bg_surface};
                border: {THEME.border_width}px solid {THEME.border_default};
                border-radius: {THEME.radius_md}px;
                color: {THEME.text_secondary};
                font-family: {THEME.font_mono};
            }}
        """)
        right_layout.addWidget(self._preview)
        
        # Options
        self._git_check = QCheckBox("Initialize git repository")
        self._git_check.setChecked(True)
        right_layout.addWidget(self._git_check)
        
        self._venv_check = QCheckBox("Create virtual environment")
        self._venv_check.setChecked(True)
        self._venv_check.setVisible(False)  # Hidden by default
        right_layout.addWidget(self._venv_check)
        
        content_layout.addLayout(right_layout, 2)
        main_layout.addLayout(content_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("Create Project")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME.accent};
                color: {THEME.text_on_accent};
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME.accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {THEME.accent_emphasis};
            }}
        """)
        create_btn.clicked.connect(self._create_project)
        btn_layout.addWidget(create_btn)
        
        main_layout.addLayout(btn_layout)

    def _populate_templates(self) -> None:
        templates = default_registry.get_templates()
        
        # Group by language
        grouped = {}
        for t in templates:
            grouped.setdefault(t.language or "Other", []).append(t)
            
        for lang in sorted(grouped.keys()):
            # Group header
            header_item = QListWidgetItem(lang)
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setBackground(Qt.GlobalColor.transparent)
            font = header_item.font()
            font.setBold(True)
            header_item.setFont(font)
            # Use color string that works in QColor constructor
            header_item.setForeground(Qt.GlobalColor.gray)
            self._template_list.addItem(header_item)
            
            for t in grouped[lang]:
                item = QListWidgetItem(self._template_list)
                item.setData(Qt.ItemDataRole.UserRole, t.template_id)
                self._templates_by_id[t.template_id] = t
                
                widget = TemplateItemWidget(t)
                item.setSizeHint(widget.sizeHint())
                self._template_list.addItem(item)
                self._template_list.setItemWidget(item, widget)
                
        if self._template_list.count() > 1:
            self._template_list.setCurrentRow(1)

    def _on_template_selected(self) -> None:
        item = self._template_list.currentItem()
        if not item:
            return
            
        template_id = item.data(Qt.ItemDataRole.UserRole)
        if not template_id:
            # It's a header
            self._preview.clear()
            self._venv_check.setVisible(False)
            return
            
        template = self._templates_by_id.get(template_id)
        if not template:
            return
            
        # Update preview (simulate creation)
        name = self._name_input.text() or "project_name"
        preview_text = f"Will generate the following for {template.name}:\\n\\n"
        preview_text += f"{name}/\\n"
        
        if template_id == "python":
            preview_text += "├── src/\\n│   └── __init__.py\\n├── main.py\\n├── requirements.txt\\n├── .gitignore\\n└── README.md"
        elif template_id == "java":
            preview_text += "├── src/\\n│   └── Main.java\\n├── .gitignore\\n└── README.md"
        elif template_id == "c":
            preview_text += "├── src/\\n│   └── main.c\\n├── Makefile\\n├── .gitignore\\n└── README.md"
        elif template_id == "cpp":
            preview_text += "├── src/\\n│   └── main.cpp\\n├── Makefile\\n├── .gitignore\\n└── README.md"
        elif template_id == "node":
            preview_text += "├── src/\\n│   └── index.js\\n├── package.json\\n├── .gitignore\\n└── README.md"
        else:
            preview_text += "├── .gitignore\\n└── README.md"
            
        self._preview.setText(preview_text)
        
        # Toggle options based on template
        self._venv_check.setVisible(template_id == "python")

    def _browse_location(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Project Location", self._loc_input.text(),
            QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self._loc_input.setText(dir_path)

    def _create_project(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a project name.")
            return
            
        loc = self._loc_input.text().strip()
        loc_path = Path(loc)
        if not loc_path.exists() or not loc_path.is_dir():
            QMessageBox.warning(self, "Invalid Location", "Please select a valid directory location.")
            return
            
        item = self._template_list.currentItem()
        if not item:
            return
            
        template_id = item.data(Qt.ItemDataRole.UserRole)
        if not template_id:
            return
            
        project_path = loc_path / name
        if project_path.exists():
            QMessageBox.warning(self, "Path Exists", f"The directory '{project_path}' already exists.")
            return
            
        try:
            # 1. Create project via manager
            created_path = self.project_manager.create_project(name, project_path, template_id)
            
            # 2. Init git if checked
            if self._git_check.isChecked():
                subprocess.run(["git", "init"], cwd=created_path, capture_output=True, check=False, creationflags=0x08000000)
                
            # 3. Create venv if python and checked
            if template_id == "python" and self._venv_check.isChecked():
                subprocess.run(["python", "-m", "venv", ".venv"], cwd=created_path, capture_output=True, check=False, creationflags=0x08000000)
                
            # 4. Emit signal
            signals.project_open_requested.emit(created_path)
            
            # 5. Close dialog
            self.accept()
            
        except Exception as e:
            LOG.error(f"Failed to create project: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create project: {e}")
