"""Environment Panel dialog for FRIDAY IDE."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QWidget, QHeaderView, QListWidget, QListWidgetItem,
    QComboBox, QMessageBox,
)

from friday_ai.core.theme import THEME
from friday_ai.core.signals import signals
from shared.logger import get_logger

LOG = get_logger("friday.env_panel")

class EnvironmentPanel(QDialog):
    """Dialog for managing toolchains, environments, and packages."""

    def __init__(self, toolchain_manager: Any, environment_manager: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.toolchain_manager = toolchain_manager
        self.environment_manager = environment_manager
        
        self.setWindowTitle("Environment Manager")
        self.resize(800, 600)
        
        self.setStyleSheet(
            f"QDialog {{ background: {THEME.bg_base}; }}"
            f"QLabel {{ color: {THEME.text_primary}; }}"
            f"QTabWidget::pane {{ border: 1px solid {THEME.border_muted}; background: {THEME.bg_base}; border-radius: {THEME.radius_sm}px; }}"
            f"QTabBar::tab {{ background: {THEME.bg_surface}; color: {THEME.text_secondary}; padding: {THEME.space_md}px {THEME.space_lg}px; border-top-left-radius: {THEME.radius_sm}px; border-top-right-radius: {THEME.radius_sm}px; margin-right: 2px; }}"
            f"QTabBar::tab:selected {{ background: {THEME.accent}; color: {THEME.text_on_accent}; }}"
            f"QTableWidget {{ background: {THEME.bg_inset}; gridline-color: {THEME.border_muted}; color: {THEME.text_primary}; border: 1px solid {THEME.border_muted}; border-radius: {THEME.radius_sm}px; }}"
            f"QHeaderView::section {{ background: {THEME.bg_surface}; color: {THEME.text_secondary}; padding: {THEME.space_sm}px; border: 1px solid {THEME.border_muted}; }}"
            f"QListWidget {{ background: {THEME.bg_inset}; color: {THEME.text_primary}; border: 1px solid {THEME.border_muted}; border-radius: {THEME.radius_sm}px; outline: none; }}"
            f"QListWidget::item {{ padding: {THEME.space_md}px; }}"
            f"QListWidget::item:selected {{ background: {THEME.bg_hover}; }}"
            f"QPushButton {{ background-color: {THEME.bg_surface}; color: {THEME.text_primary}; border: 1px solid {THEME.border_default}; border-radius: {THEME.radius_md}px; padding: {THEME.space_sm}px {THEME.space_lg}px; }}"
            f"QPushButton:hover {{ background-color: {THEME.bg_hover}; border-color: {THEME.text_muted}; }}"
            f"QLineEdit {{ background: {THEME.bg_inset}; color: {THEME.text_primary}; border: 1px solid {THEME.border_default}; border-radius: {THEME.radius_md}px; padding: {THEME.space_sm}px {THEME.space_md}px; }}"
        )
        
        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_xl, THEME.space_xl, THEME.space_xl, THEME.space_xl)
        layout.setSpacing(THEME.space_lg)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Runtimes
        self.tab_runtimes = QWidget()
        self._build_runtimes_tab()
        self.tabs.addTab(self.tab_runtimes, "Runtimes")

        # Tab 2: Environments
        self.tab_envs = QWidget()
        self._build_envs_tab()
        self.tabs.addTab(self.tab_envs, "Environments")

        # Tab 3: Packages
        self.tab_packages = QWidget()
        self._build_packages_tab()
        self.tabs.addTab(self.tab_packages, "Packages")
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _build_runtimes_tab(self) -> None:
        layout = QVBoxLayout(self.tab_runtimes)
        layout.setContentsMargins(THEME.space_lg, THEME.space_lg, THEME.space_lg, THEME.space_lg)
        layout.setSpacing(THEME.space_md)

        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._refresh_runtimes)
        toolbar.addStretch()
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        # Table
        self.runtimes_table = QTableWidget()
        self.runtimes_table.setColumnCount(4)
        self.runtimes_table.setHorizontalHeaderLabels(["Name", "Type", "Version", "Path"])
        self.runtimes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.runtimes_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.runtimes_table.setAlternatingRowColors(True)
        self.runtimes_table.setStyleSheet(
            f"alternate-background-color: {THEME.bg_surface};"
        )
        self.runtimes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.runtimes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.runtimes_table.verticalHeader().setVisible(False)
        
        layout.addWidget(self.runtimes_table)

    def _build_envs_tab(self) -> None:
        layout = QVBoxLayout(self.tab_envs)
        layout.setContentsMargins(THEME.space_lg, THEME.space_lg, THEME.space_lg, THEME.space_lg)
        layout.setSpacing(THEME.space_md)

        # Toolbar
        toolbar = QHBoxLayout()
        create_btn = QPushButton("Create Environment")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(f"QPushButton {{ background-color: {THEME.accent}; color: {THEME.text_on_accent}; border: none; }} QPushButton:hover {{ background-color: {THEME.accent_hover}; }}")
        create_btn.clicked.connect(self._show_create_env_dialog)
        
        activate_btn = QPushButton("Activate")
        activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        activate_btn.clicked.connect(self._activate_selected_env)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.clicked.connect(self._remove_selected_env)
        
        toolbar.addWidget(create_btn)
        toolbar.addStretch()
        toolbar.addWidget(activate_btn)
        toolbar.addWidget(remove_btn)
        layout.addLayout(toolbar)

        # List
        self.envs_list = QListWidget()
        layout.addWidget(self.envs_list)

    def _build_packages_tab(self) -> None:
        layout = QVBoxLayout(self.tab_packages)
        layout.setContentsMargins(THEME.space_lg, THEME.space_lg, THEME.space_lg, THEME.space_lg)
        layout.setSpacing(THEME.space_md)

        # Top bar
        top_bar = QHBoxLayout()
        self.pkg_search = QLineEdit()
        self.pkg_search.setPlaceholderText("Search packages...")
        self.pkg_search.textChanged.connect(self._filter_packages)
        
        self.pkg_install_input = QLineEdit()
        self.pkg_install_input.setPlaceholderText("Package to install...")
        
        install_btn = QPushButton("Install")
        install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        install_btn.setStyleSheet(f"QPushButton {{ background-color: {THEME.accent}; color: {THEME.text_on_accent}; border: none; }} QPushButton:hover {{ background-color: {THEME.accent_hover}; }}")
        install_btn.clicked.connect(self._install_package)
        
        top_bar.addWidget(self.pkg_search)
        top_bar.addSpacing(THEME.space_xl)
        top_bar.addWidget(self.pkg_install_input)
        top_bar.addWidget(install_btn)
        layout.addLayout(top_bar)

        # Table
        self.pkgs_table = QTableWidget()
        self.pkgs_table.setColumnCount(3)
        self.pkgs_table.setHorizontalHeaderLabels(["Name", "Version", "Latest"])
        self.pkgs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pkgs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pkgs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pkgs_table.verticalHeader().setVisible(False)
        self.pkgs_table.setAlternatingRowColors(True)
        self.pkgs_table.setStyleSheet(
            f"alternate-background-color: {THEME.bg_surface};"
        )
        layout.addWidget(self.pkgs_table)

        # Bottom actions
        action_bar = QHBoxLayout()
        upgrade_btn = QPushButton("Upgrade")
        upgrade_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        upgrade_btn.clicked.connect(self._upgrade_package)
        
        uninstall_btn = QPushButton("Uninstall")
        uninstall_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        uninstall_btn.clicked.connect(self._uninstall_package)
        
        action_bar.addStretch()
        action_bar.addWidget(upgrade_btn)
        action_bar.addWidget(uninstall_btn)
        layout.addLayout(action_bar)

    def _load_data(self) -> None:
        self._refresh_runtimes()
        self._refresh_envs()
        self._refresh_packages()

    def _refresh_runtimes(self) -> None:
        try:
            runtimes = self.toolchain_manager.get_all()
            self.runtimes_table.setRowCount(len(runtimes))
            for i, rt in enumerate(runtimes):
                self.runtimes_table.setItem(i, 0, QTableWidgetItem(str(rt.name)))
                self.runtimes_table.setItem(i, 1, QTableWidgetItem(str(rt.tool_type)))
                self.runtimes_table.setItem(i, 2, QTableWidgetItem(str(rt.version)))
                self.runtimes_table.setItem(i, 3, QTableWidgetItem(str(rt.path)))
        except Exception as e:
            LOG.error(f"Failed to load runtimes: {e}")

    def _refresh_envs(self) -> None:
        self.envs_list.clear()
        try:
            # Based on requirements, the method to get envs might be one of these, or we detect in CWD
            envs = []
            if hasattr(self.environment_manager, "get_all"):
                envs = self.environment_manager.get_all()
            elif hasattr(self.environment_manager, "get_environments"):
                envs = self.environment_manager.get_environments()
            elif hasattr(self.environment_manager, "detect_project_environment"):
                # fallback for detecting from cwd if no list method is exposed
                env = self.environment_manager.detect_project_environment(Path.cwd())
                if env:
                    envs = [env]
                
            for env in envs:
                item = QListWidgetItem()
                # Status indicators
                is_active = getattr(env, "is_active", False)
                status_color = "#34D399" if is_active else "#F87171"
                status = "●" if is_active else "○"
                
                # HTML styling for rich text isn't directly supported in QListWidgetItem without a delegate, 
                # so we will use plain text for now, but we can set the text color if we wanted.
                # However, basic string is requested.
                env_type = getattr(env, "env_type", "Unknown")
                interpreter_path = getattr(env, "interpreter_path", getattr(env, "path", ""))
                
                text = f"{status} {env.name} ({env_type}) - {interpreter_path}"
                item.setText(text)
                
                if is_active:
                    # Highlight active with a slight color shift
                    pass
                
                item.setData(Qt.ItemDataRole.UserRole, getattr(env, "path", None))
                self.envs_list.addItem(item)
        except Exception as e:
            LOG.error(f"Failed to load environments: {e}")

    def _show_create_env_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Environment")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet(
            f"QDialog {{ background: {THEME.bg_overlay}; }}"
            f"QLabel {{ color: {THEME.text_primary}; }}"
            f"QLineEdit {{ background: {THEME.bg_inset}; color: {THEME.text_primary}; border: 1px solid {THEME.border_default}; border-radius: {THEME.radius_md}px; padding: {THEME.space_sm}px; }}"
            f"QComboBox {{ background: {THEME.bg_inset}; color: {THEME.text_primary}; border: 1px solid {THEME.border_default}; border-radius: {THEME.radius_md}px; padding: {THEME.space_sm}px; }}"
            f"QPushButton {{ background-color: {THEME.bg_surface}; color: {THEME.text_primary}; border: 1px solid {THEME.border_default}; border-radius: {THEME.radius_md}px; padding: {THEME.space_sm}px {THEME.space_lg}px; }}"
            f"QPushButton:hover {{ background-color: {THEME.bg_hover}; border-color: {THEME.text_muted}; }}"
        )
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(THEME.space_md)
        layout.setContentsMargins(THEME.space_xl, THEME.space_xl, THEME.space_xl, THEME.space_xl)
        
        layout.addWidget(QLabel("Environment Name:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g. .venv")
        layout.addWidget(name_input)
        
        layout.addWidget(QLabel("Python Version / Runtime:"))
        runtime_combo = QComboBox()
        try:
            runtimes = self.toolchain_manager.get_all()
            for rt in runtimes:
                runtime_combo.addItem(f"{rt.name} ({rt.version})", rt)
        except Exception:
            pass
        layout.addWidget(runtime_combo)
        
        layout.addSpacing(THEME.space_lg)
        
        btns = QHBoxLayout()
        create_btn = QPushButton("Create")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(f"QPushButton {{ background-color: {THEME.accent}; color: {THEME.text_on_accent}; border: none; }} QPushButton:hover {{ background-color: {THEME.accent_hover}; }}")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(create_btn)
        layout.addLayout(btns)
        
        def on_create():
            try:
                name = name_input.text().strip()
                runtime = runtime_combo.currentData()
                if name and runtime:
                    # Using PYTHON_VENV as type based on requirement hint
                    self.environment_manager.create_environment(name, "PYTHON_VENV", runtime)
                    self._refresh_envs()
                    dialog.accept()
            except Exception as e:
                LOG.error(f"Failed to create environment: {e}")
                QMessageBox.critical(dialog, "Error", f"Failed to create environment: {e}")
                
        create_btn.clicked.connect(on_create)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()

    def _activate_selected_env(self) -> None:
        item = self.envs_list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        try:
            self.environment_manager.activate_environment(path)
            self._refresh_envs()
            self._refresh_packages()
        except Exception as e:
            LOG.error(f"Failed to activate environment: {e}")
            QMessageBox.critical(self, "Error", f"Failed to activate environment: {e}")

    def _remove_selected_env(self) -> None:
        item = self.envs_list.currentItem()
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        try:
            self.environment_manager.remove_environment(path)
            self._refresh_envs()
        except Exception as e:
            LOG.error(f"Failed to remove environment: {e}")
            QMessageBox.critical(self, "Error", f"Failed to remove environment: {e}")

    def _refresh_packages(self) -> None:
        env_path = self._get_active_env_path()
        if not env_path:
            self.pkgs_table.setRowCount(0)
            return

        try:
            packages = self.environment_manager.list_packages(env_path)
            self.pkgs_table.setRowCount(len(packages))
            for i, pkg in enumerate(packages):
                self.pkgs_table.setItem(i, 0, QTableWidgetItem(str(getattr(pkg, "name", pkg))))
                self.pkgs_table.setItem(i, 1, QTableWidgetItem(str(getattr(pkg, "version", ""))))
                self.pkgs_table.setItem(i, 2, QTableWidgetItem(str(getattr(pkg, "latest_version", ""))))
        except Exception as e:
            LOG.error(f"Failed to list packages: {e}")

    def _get_active_env_path(self) -> str | None:
        for i in range(self.envs_list.count()):
            item = self.envs_list.item(i)
            if "●" in item.text():
                return item.data(Qt.ItemDataRole.UserRole)
        # Fallback to the first selected item
        item = self.envs_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _filter_packages(self, text: str) -> None:
        text = text.lower()
        for i in range(self.pkgs_table.rowCount()):
            item = self.pkgs_table.item(i, 0)
            if item:
                match = text in item.text().lower()
                self.pkgs_table.setRowHidden(i, not match)

    def _install_package(self) -> None:
        pkg_name = self.pkg_install_input.text().strip()
        env_path = self._get_active_env_path()
        if not pkg_name or not env_path:
            return
        try:
            self.environment_manager.install_package(pkg_name, env_path)
            self.pkg_install_input.clear()
            self._refresh_packages()
        except Exception as e:
            LOG.error(f"Failed to install package: {e}")
            QMessageBox.critical(self, "Error", f"Failed to install package {pkg_name}: {e}")

    def _upgrade_package(self) -> None:
        row = self.pkgs_table.currentRow()
        env_path = self._get_active_env_path()
        if row < 0 or not env_path:
            return
        item = self.pkgs_table.item(row, 0)
        if not item:
            return
        pkg_name = item.text()
        try:
            self.environment_manager.upgrade_package(pkg_name, env_path)
            self._refresh_packages()
        except Exception as e:
            LOG.error(f"Failed to upgrade package: {e}")
            QMessageBox.critical(self, "Error", f"Failed to upgrade package {pkg_name}: {e}")

    def _uninstall_package(self) -> None:
        row = self.pkgs_table.currentRow()
        env_path = self._get_active_env_path()
        if row < 0 or not env_path:
            return
        item = self.pkgs_table.item(row, 0)
        if not item:
            return
        pkg_name = item.text()
        try:
            self.environment_manager.uninstall_package(pkg_name, env_path)
            self._refresh_packages()
        except Exception as e:
            LOG.error(f"Failed to uninstall package: {e}")
            QMessageBox.critical(self, "Error", f"Failed to uninstall package {pkg_name}: {e}")
