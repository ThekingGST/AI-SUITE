"""Application menu bar.

Implements File, Edit, View, Run, Terminal, and Help menus.
Wires actions to the main window or global signal bus.
"""
from __future__ import annotations
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QMenu, QMenuBar, QWidget
from friday_ai.core.signals import signals


class FridayMenuBar(QMenuBar):
    """The main application menu bar."""

    def __init__(self, main_window: QWidget) -> None:
        super().__init__(main_window)
        self._main = main_window
        self._build_menus()

    def _build_menus(self) -> None:
        self._build_file_menu()
        self._build_edit_menu()
        self._build_view_menu()
        self._build_run_menu()
        self._build_terminal_menu()
        self._build_help_menu()

    def _build_file_menu(self) -> None:
        file_menu = self.addMenu("&File")

        # New Project
        new_proj = QAction("New Project...", self)
        new_proj.setShortcut(QKeySequence("Ctrl+N"))
        new_proj.triggered.connect(lambda: signals.project_create_requested.emit())
        file_menu.addAction(new_proj)

        # New File Submenu
        new_menu = file_menu.addMenu("New...")
        
        file_types = [
            "Python File", "Python Package", "Java Class", 
            "C Source", "C++ Source", "JavaScript File",
            "JSON File", "Markdown File", "Text File"
        ]
        for ftype in file_types:
            act = QAction(ftype, self)
            act.triggered.connect(lambda checked, t=ftype: signals.file_new_requested.emit(t))
            new_menu.addAction(act)
            
        new_menu.addSeparator()
        new_folder = QAction("Folder", self)
        new_folder.triggered.connect(lambda: signals.file_new_requested.emit("Folder"))
        new_menu.addAction(new_folder)
        
        file_menu.addSeparator()

        # Open Project
        open_proj = QAction("Open Project...", self)
        open_proj.setShortcut(QKeySequence("Ctrl+O"))
        open_proj.triggered.connect(self._main._on_open_project_shortcut)
        file_menu.addAction(open_proj)

        file_menu.addSeparator()

        # Save
        save = QAction("Save", self)
        save.setShortcut(QKeySequence("Ctrl+S"))
        # We can trigger the save action on the editor area if we had a direct ref,
        # but since we want loose coupling, we'll tell main to handle it, or editor area.
        # Actually, editor area intercepts Ctrl+S. So we just need a signal.
        # However, for simplicity, we can let the shortcut handle it, but clicking the menu needs to work.
        # Let's add a save_requested signal.
        save.triggered.connect(lambda: getattr(self._main._editor, "_save_current", lambda: None)())
        file_menu.addAction(save)

        # Save As
        save_as = QAction("Save As...", self)
        save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as.triggered.connect(lambda: getattr(self._main._editor, "_save_as_current", lambda: None)())
        file_menu.addAction(save_as)

        # Save All
        save_all = QAction("Save All", self)
        save_all.triggered.connect(lambda: getattr(self._main._editor, "_save_all", lambda: None)())
        file_menu.addAction(save_all)

        file_menu.addSeparator()
        
        # Settings
        settings_act = QAction("Settings", self)
        settings_act.setShortcut(QKeySequence("Ctrl+,"))
        settings_act.triggered.connect(self._main.open_settings)
        file_menu.addAction(settings_act)

        file_menu.addSeparator()

        # Close Tab
        close_tab = QAction("Close Tab", self)
        close_tab.setShortcut(QKeySequence("Ctrl+W"))
        close_tab.triggered.connect(lambda: getattr(self._main._editor._tab_bar, "_on_close_clicked", lambda x: None)(self._main._editor._tab_bar._current_index))
        file_menu.addAction(close_tab)

        file_menu.addSeparator()

        # Manage Environments
        env_act = QAction("Manage Environments...", self)
        env_act.triggered.connect(self._main._show_environment_panel)
        file_menu.addAction(env_act)

        file_menu.addSeparator()


    def _build_edit_menu(self) -> None:
        edit_menu = self.addMenu("&Edit")

        find = QAction("Find", self)
        find.setShortcut(QKeySequence("Ctrl+F"))
        find.triggered.connect(lambda: getattr(self._main._editor, "_open_find", lambda: None)())
        edit_menu.addAction(find)

        replace = QAction("Replace", self)
        replace.setShortcut(QKeySequence("Ctrl+H"))
        replace.triggered.connect(lambda: getattr(self._main._editor, "_open_replace", lambda: None)())
        edit_menu.addAction(replace)

        find_proj = QAction("Find in Project", self)
        find_proj.setShortcut(QKeySequence("Ctrl+Shift+F"))
        find_proj.triggered.connect(self._main.show_search)
        edit_menu.addAction(find_proj)

        edit_menu.addSeparator()

        goto = QAction("Go to Line...", self)
        goto.setShortcut(QKeySequence("Ctrl+G"))
        goto.triggered.connect(lambda: getattr(self._main._editor, "go_to_line", lambda: None)())
        edit_menu.addAction(goto)

        dup = QAction("Duplicate Line", self)
        dup.setShortcut(QKeySequence("Ctrl+D"))
        dup.triggered.connect(lambda: getattr(self._main._editor, "duplicate_line", lambda: None)())
        edit_menu.addAction(dup)

        comment = QAction("Toggle Comment", self)
        comment.setShortcut(QKeySequence("Ctrl+/"))
        comment.triggered.connect(lambda: getattr(self._main._editor, "toggle_comment", lambda: None)())
        edit_menu.addAction(comment)

    def _build_view_menu(self) -> None:
        view_menu = self.addMenu("&View")

        toggle_exp = QAction("Toggle Explorer", self)
        toggle_exp.setShortcut(QKeySequence("Ctrl+B"))
        toggle_exp.triggered.connect(lambda: self._main._sidebar.setVisible(not self._main._sidebar.isVisible()))
        view_menu.addAction(toggle_exp)

        toggle_bot = QAction("Toggle Bottom Panel", self)
        toggle_bot.setShortcut(QKeySequence("Ctrl+J"))
        toggle_bot.triggered.connect(lambda: self._main._bottom_panel.setVisible(not self._main._bottom_panel.isVisible()))
        view_menu.addAction(toggle_bot)

        toggle_ws = QAction("Toggle Workspace Panel", self)
        toggle_ws.triggered.connect(lambda: self._main._workspace_panel.setVisible(not self._main._workspace_panel.isVisible()))
        view_menu.addAction(toggle_ws)

        view_menu.addSeparator()

        fs = QAction("Full Screen", self)
        fs.setShortcut(QKeySequence("F11"))
        fs.triggered.connect(lambda: self._main.showNormal() if self._main.isFullScreen() else self._main.showFullScreen())
        view_menu.addAction(fs)

    def _build_run_menu(self) -> None:
        run_menu = self.addMenu("&Run")

        run_proj = QAction("Run Project", self)
        run_proj.setShortcut(QKeySequence("F5"))
        run_proj.triggered.connect(lambda: signals.run_project_requested.emit())
        run_menu.addAction(run_proj)

        run_file = QAction("Run Current File", self)
        run_file.setShortcut(QKeySequence("Ctrl+F5"))
        run_file.triggered.connect(self._main.run_current_file)
        run_menu.addAction(run_file)

        run_menu.addSeparator()

        stop = QAction("Stop Execution", self)
        stop.setShortcut(QKeySequence("Shift+F5"))
        stop.triggered.connect(lambda: signals.run_stop_requested.emit())
        run_menu.addAction(stop)

    def _build_terminal_menu(self) -> None:
        term_menu = self.addMenu("&Terminal")

        new_term = QAction("New Terminal", self)
        new_term.setShortcut(QKeySequence("Ctrl+Shift+`"))
        new_term.triggered.connect(self._main.new_terminal)
        term_menu.addAction(new_term)

    def _build_help_menu(self) -> None:
        help_menu = self.addMenu("&Help")

        about = QAction("About FRIDAY", self)
        about.triggered.connect(lambda: signals.mission_update.emit("INFO", "FRIDAY AI IDE v1.0"))
        help_menu.addAction(about)
