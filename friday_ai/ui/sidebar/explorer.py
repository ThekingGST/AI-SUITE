"""Real file explorer panel.

Production-quality file tree powered by ``QFileSystemModel``.  Features:

    * Real directory tree from the opened project
    * Lazy loading (handles large projects)
    * Auto-refresh via Qt's built-in filesystem watching
    * Double-click to open files
    * Right-click context menu:
        - Open, Copy Path, Copy Relative Path, Reveal in Explorer
        - New File, New Folder, Rename, Delete
    * Themed styling from the design system
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import QDir, QModelIndex, QSortFilterProxyModel, Qt
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileSystemModel,
    QFileIconProvider,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from friday_ai.core.icons import Icons
from friday_ai.core.signals import signals
from friday_ai.core.theme import THEME
from shared.logger import get_logger

LOG = get_logger("friday.explorer")


class _ProjectFilter(QSortFilterProxyModel):
    """Hides noisy directories like __pycache__, .git, node_modules."""

    _HIDDEN = frozenset({
        "__pycache__", ".git", ".svn", ".hg", "node_modules", ".venv",
        "venv", ".tox", ".mypy_cache", ".pytest_cache", ".idea", ".vs",
        ".DS_Store",
    })

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex,
    ) -> bool:
        model = self.sourceModel()
        if model is None:
            return True
        index = model.index(source_row, 0, source_parent)
        name = model.fileName(index)
        return name not in self._HIDDEN

class _FridayIconProvider(QFileIconProvider):
    """Provides SVG icons for the file explorer based on type."""
    def icon(self, info):
        # We need to import QFileInfo if it's passed as QFileInfo
        from PyQt5.QtCore import QFileInfo
        from PyQt5.QtGui import QIcon
        
        if isinstance(info, QFileInfo):
            if info.isDir():
                return Icons.get("folder", color=THEME.accent_muted)
            
            ext = info.suffix().lower()
            if ext in ("py", "pyw"):
                return Icons.get("code", color="#3572A5")
            elif ext in ("md", "txt", "rst"):
                return Icons.get("file-text", color=THEME.text_secondary)
            elif ext in ("json", "yaml", "yml", "toml", "ini"):
                return Icons.get("settings", color=THEME.warning)
            elif ext in ("png", "jpg", "jpeg", "svg", "gif"):
                return Icons.get("image", color=THEME.success)
            else:
                return Icons.get("file", color=THEME.text_muted)
        
        # Fallback to base
        return super().icon(info)


class FileExplorer(QWidget):
    """File tree panel backed by the real filesystem."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project_root: Path | None = None
        self._build_ui()
        self._connect_signals()

    # ── Construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(
            THEME.space_xl, THEME.space_lg, THEME.space_md, THEME.space_lg,
        )

        self._title = QLabel("EXPLORER")
        self._title.setStyleSheet(
            f"color: {THEME.text_secondary}; "
            f"font-size: {THEME.font_size_xs}px; "
            "font-weight: bold; "
            "letter-spacing: 1px; "
            "background: transparent;"
        )
        header_layout.addWidget(self._title)
        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton()
        refresh_btn.setIcon(Icons.get("search", color=THEME.text_muted, size=14))
        refresh_btn.setFixedSize(22, 22)
        refresh_btn.setToolTip("Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"border-radius: {THEME.radius_sm}px; }}"
            f"QPushButton:hover {{ background: {THEME.bg_hover}; }}"
        )
        refresh_btn.clicked.connect(self._refresh)
        header_layout.addWidget(refresh_btn)

        # Reveal Active button
        reveal_active_btn = QPushButton()
        reveal_active_btn.setIcon(Icons.get("target", color=THEME.text_muted, size=14))
        reveal_active_btn.setFixedSize(22, 22)
        reveal_active_btn.setToolTip("Reveal Active File")
        reveal_active_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reveal_active_btn.setStyleSheet(refresh_btn.styleSheet())
        reveal_active_btn.clicked.connect(self._reveal_active)
        header_layout.addWidget(reveal_active_btn)

        layout.addWidget(header)

        # File system model
        self._fs_model = QFileSystemModel()
        self._icon_provider = _FridayIconProvider()
        self._fs_model.setIconProvider(self._icon_provider)
        self._fs_model.setReadOnly(False)
        self._fs_model.setFilter(
            QDir.Filter.AllDirs
            | QDir.Filter.Files
            | QDir.Filter.NoDotAndDotDot
        )

        # Proxy filter
        self._proxy = _ProjectFilter()
        self._proxy.setSourceModel(self._fs_model)
        self._proxy.setDynamicSortFilter(True)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        # Tree view
        self._tree = QTreeView()
        self._tree.setModel(self._proxy)
        self._tree.setHeaderHidden(True)
        self._tree.setIndentation(THEME.space_xl)
        self._tree.setAnimated(True)
        self._tree.setExpandsOnDoubleClick(True)
        self._tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection,
        )
        self._tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu,
        )
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Hide all columns except Name.
        for col in range(1, 4):
            self._tree.setColumnHidden(col, True)

        # Signals
        self._tree.doubleClicked.connect(self._on_double_click)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self._tree, stretch=1)

        # Placeholder message (shown when no project is open).
        self._placeholder = QLabel("Open a project to browse files")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet(
            f"color: {THEME.text_muted}; "
            f"font-size: {THEME.font_size_sm}px; "
            "background: transparent; "
            f"padding: {THEME.space_2xl}px;"
        )
        layout.addWidget(self._placeholder)

        # Start with placeholder visible, tree hidden.
        self._tree.setVisible(False)
        self._placeholder.setVisible(True)

    # ── Signal wiring ────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        signals.project_opened.connect(self._on_project_opened)
        signals.project_closed.connect(self._on_project_closed)
        signals.file_opened.connect(self._on_file_opened)
        signals.file_new_requested.connect(self._on_file_new_requested)

    def _on_file_opened(self, path: str) -> None:
        self._active_file = path

    # ── Project lifecycle ────────────────────────────────────────────────

    def _on_project_opened(self, path: str) -> None:
        root = Path(path)
        self._project_root = root
        self._title.setText(root.name.upper())

        root_index = self._fs_model.setRootPath(str(root))
        proxy_root = self._proxy.mapFromSource(root_index)
        self._tree.setRootIndex(proxy_root)
        self._proxy.sort(0, Qt.SortOrder.AscendingOrder)

        self._placeholder.setVisible(False)
        self._tree.setVisible(True)

        signals.mission_update.emit("SCAN", "Populating file explorer...")

    def _on_project_closed(self) -> None:
        self._project_root = None
        self._title.setText("EXPLORER")
        self._tree.setVisible(False)
        self._placeholder.setVisible(True)

    # ── User interactions ────────────────────────────────────────────────

    def _on_double_click(self, proxy_index: QModelIndex) -> None:
        source_index = self._proxy.mapToSource(proxy_index)
        path = self._fs_model.filePath(source_index)
        if path and not self._fs_model.isDir(source_index):
            signals.file_open_requested.emit(path)

    def _get_selected_dir(self) -> str:
        """Returns the directory of the currently selected item, or project root."""
        if not self._project_root:
            return ""
        indexes = self._tree.selectedIndexes()
        if not indexes:
            return str(self._project_root)
        source_index = self._proxy.mapToSource(indexes[0])
        path = self._fs_model.filePath(source_index)
        return path if self._fs_model.isDir(source_index) else str(Path(path).parent)

    def _on_file_new_requested(self, file_type: str) -> None:
        parent_dir = self._get_selected_dir()
        if parent_dir:
            if file_type == "Folder":
                self._create_folder(parent_dir)
            else:
                self._create_templated_file(parent_dir, file_type)

    def _on_context_menu(self, position) -> None:
        proxy_index = self._tree.indexAt(position)
        if not proxy_index.isValid():
            # Clicked on empty space — show "New File / New Folder" only.
            self._show_empty_context_menu(position)
            return

        source_index = self._proxy.mapToSource(proxy_index)
        path = self._fs_model.filePath(source_index)
        is_dir = self._fs_model.isDir(source_index)

        menu = self._styled_menu()

        if not is_dir:
            open_action = QAction("Open", self)
            open_action.triggered.connect(
                lambda: signals.file_open_requested.emit(path),
            )
            menu.addAction(open_action)
            menu.addSeparator()

        self._build_new_menu(menu, path if is_dir else str(Path(path).parent))

        menu.addSeparator()

        # Rename
        rename = QAction("Rename...", self)
        rename.setShortcut(QKeySequence("F2"))
        rename.triggered.connect(lambda: self._rename(path))
        menu.addAction(rename)

        # Delete
        delete = QAction("Delete", self)
        delete.setShortcut(QKeySequence("Delete"))
        delete.triggered.connect(lambda: self._delete(path))
        menu.addAction(delete)

        menu.addSeparator()

        if not is_dir:
            # Duplicate
            duplicate = QAction("Duplicate", self)
            duplicate.triggered.connect(lambda: self._duplicate(path))
            menu.addAction(duplicate)
            menu.addSeparator()

        # Copy path
        copy_path = QAction("Copy Path", self)
        copy_path.triggered.connect(lambda: self._copy_to_clipboard(path))
        menu.addAction(copy_path)

        if self._project_root is not None:
            copy_rel = QAction("Copy Relative Path", self)
            try:
                rel = str(Path(path).relative_to(self._project_root))
            except ValueError:
                rel = path
            copy_rel.triggered.connect(lambda: self._copy_to_clipboard(rel))
            menu.addAction(copy_rel)

        menu.addSeparator()

        reveal = QAction("Reveal in File Explorer", self)
        reveal.triggered.connect(lambda: self._reveal_in_explorer(path))
        menu.addAction(reveal)

        menu.exec(self._tree.viewport().mapToGlobal(position))

    def _show_empty_context_menu(self, position) -> None:
        if self._project_root is None:
            return
        menu = self._styled_menu()
        root = str(self._project_root)

        self._build_new_menu(menu, root)

        menu.exec(self._tree.viewport().mapToGlobal(position))

    def _build_new_menu(self, parent_menu: QMenu, target_dir: str) -> None:
        new_menu = parent_menu.addMenu("New...")
        new_menu.setStyleSheet(parent_menu.styleSheet())
        
        file_types = [
            "Python File", "Python Package", "Java Class", 
            "C Source", "C++ Source", "JavaScript File",
            "JSON File", "Markdown File", "Text File"
        ]
        
        for ftype in file_types:
            act = QAction(ftype, self)
            act.triggered.connect(lambda checked, t=ftype, d=target_dir: self._create_templated_file(d, t))
            new_menu.addAction(act)
            
        new_menu.addSeparator()
        new_folder = QAction("Folder", self)
        new_folder.triggered.connect(lambda: self._create_folder(target_dir))
        new_menu.addAction(new_folder)

    def _styled_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ "
            f"  background: {THEME.bg_overlay}; "
            f"  border: {THEME.border_width}px solid {THEME.border_default}; "
            f"  border-radius: {THEME.radius_md}px; "
            f"  padding: {THEME.space_sm}px 0; "
            f"}} "
            f"QMenu::item {{ "
            f"  padding: {THEME.space_md}px {THEME.space_xl}px; "
            f"  color: {THEME.text_primary}; "
            f"}} "
            f"QMenu::item:selected {{ "
            f"  background: {THEME.accent_muted}; "
            f"}}"
        )
        return menu

    # ── File operations ──────────────────────────────────────────────────

    def _create_templated_file(self, parent_dir: str, file_type: str) -> None:
        default_names = {
            "Python File": "main.py",
            "Python Package": "new_package",
            "Java Class": "Main.java",
            "C Source": "main.c",
            "C++ Source": "main.cpp",
            "JavaScript File": "index.js",
            "JSON File": "data.json",
            "Markdown File": "README.md",
            "Text File": "notes.txt"
        }
        name, ok = QInputDialog.getText(self, f"New {file_type}", "Name:", text=default_names.get(file_type, "new_file"))
        if not ok or not name:
            return
            
        path = Path(parent_dir) / name
        try:
            if file_type == "Python Package":
                path.mkdir(parents=True, exist_ok=True)
                init_path = path / "__init__.py"
                init_path.touch()
                signals.mission_update.emit("CREATE", f"Created package {name}")
                LOG.info("Created package: %s", path)
                signals.file_open_requested.emit(str(init_path))
                return

            # Starter templates
            content = ""
            if file_type == "Python File" and name == "main.py":
                content = 'def main():\n    print("Hello from Python!")\n\nif __name__ == "__main__":\n    main()\n'
            elif file_type == "Java Class":
                class_name = path.stem
                content = f'public class {class_name} {{\n    public static void main(String[] args) {{\n        System.out.println("Hello from Java!");\n    }}\n}}\n'
            elif file_type == "C Source":
                content = '#include <stdio.h>\n\nint main() {\n    printf("Hello from C!\\n");\n    return 0;\n}\n'
            elif file_type == "C++ Source":
                content = '#include <iostream>\n\nint main() {\n    std::cout << "Hello from C++!" << std::endl;\n    return 0;\n}\n'
            elif file_type == "JavaScript File":
                content = 'console.log("Hello from Node.js!");\n'
            elif file_type == "JSON File":
                content = '{\n    \n}\n'
            
            path.write_text(content, encoding="utf-8")
            signals.mission_update.emit("CREATE", f"Created {name}")
            LOG.info("Created file: %s", path)
            signals.file_open_requested.emit(str(path))
        except OSError as e:
            signals.mission_update.emit("ERROR", f"Cannot create: {e}")

    def _create_folder(self, parent_dir: str) -> None:
        name, ok = QInputDialog.getText(
            self, "New Folder", "Folder name:",
        )
        if ok and name:
            path = Path(parent_dir) / name
            try:
                path.mkdir(parents=True, exist_ok=True)
                signals.mission_update.emit("CREATE", f"Created folder {name}")
                LOG.info("Created folder: %s", path)
            except OSError as e:
                signals.mission_update.emit("ERROR", f"Cannot create: {e}")

    def _rename(self, path: str) -> None:
        old_name = Path(path).name
        new_name, ok = QInputDialog.getText(
            self, "Rename", "New name:", text=old_name,
        )
        if ok and new_name and new_name != old_name:
            new_path = Path(path).parent / new_name
            try:
                Path(path).rename(new_path)
                signals.mission_update.emit("RENAME", f"{old_name} -> {new_name}")
                LOG.info("Renamed: %s -> %s", path, new_path)
            except OSError as e:
                signals.mission_update.emit("ERROR", f"Cannot rename: {e}")

    def _delete(self, path: str) -> None:
        name = Path(path).name
        is_dir = Path(path).is_dir()
        msg = f"Delete {'folder' if is_dir else 'file'} '{name}'?"
        if is_dir:
            msg += "\n\nThis will delete all contents."

        reply = QMessageBox.question(
            self, "Confirm Delete", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            p = Path(path)
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()
            signals.mission_update.emit("DELETE", f"Deleted {name}")
            LOG.info("Deleted: %s", path)
        except OSError as e:
            signals.mission_update.emit("ERROR", f"Cannot delete: {e}")

    def _duplicate(self, path: str) -> None:
        p = Path(path)
        new_p = p.with_name(f"{p.stem}_copy{p.suffix}")
        count = 1
        while new_p.exists():
            new_p = p.with_name(f"{p.stem}_copy{count}{p.suffix}")
            count += 1
        try:
            import shutil
            shutil.copy2(p, new_p)
            signals.mission_update.emit("DUPLICATE", f"Duplicated {p.name}")
            LOG.info("Duplicated: %s -> %s", p, new_p)
            signals.file_open_requested.emit(str(new_p))
        except OSError as e:
            signals.mission_update.emit("ERROR", f"Cannot duplicate: {e}")

    # ── Utilities ────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        if self._project_root is not None:
            root_index = self._fs_model.setRootPath(str(self._project_root))
            proxy_root = self._proxy.mapFromSource(root_index)
            self._tree.setRootIndex(proxy_root)
            signals.mission_update.emit("SCAN", "Refreshed file explorer")

    @staticmethod
    def _copy_to_clipboard(text: str) -> None:
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

    @staticmethod
    def _reveal_in_explorer(path: str) -> None:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", str(Path(path).parent)])

    def _reveal_active(self) -> None:
        if getattr(self, "_active_file", None) and self._project_root:
            index = self._fs_model.index(self._active_file)
            if index.isValid():
                proxy_index = self._proxy.mapFromSource(index)
                if proxy_index.isValid():
                    self._tree.scrollTo(proxy_index)
                    self._tree.setCurrentIndex(proxy_index)
