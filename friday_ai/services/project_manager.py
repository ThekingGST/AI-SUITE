"""Project management service.

Handles opening, closing, and tracking projects.  This is pure business logic
with zero UI knowledge — it communicates exclusively through signals.

Responsibilities:
    * Validate that a path is a valid project directory
    * Track the currently open project
    * Maintain a recent-projects list (persisted via the persistence service)
    * Scan the project for file statistics on a background thread
    * Emit signals so the UI can react (explorer, status bar, mission control)
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import hashlib
from PyQt5.QtCore import QObject

from friday_ai.core.signals import signals
from friday_ai.core.workers import BackgroundWorker
from shared.logger import get_logger
from shared.config.config_manager import ConfigManager

LOG = get_logger("friday.project")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ProjectType(Enum):
    """Detected project type based on file inspection."""
    PYTHON = "python"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    NODE = "node"
    RUST = "rust"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass
class ProjectMetadata:
    """Metadata stored in %LOCALAPPDATA%/AISuite/friday/projects/ within each project's hash directory."""
    name: str
    project_type: str = "unknown"
    created: str = ""
    main_file: str | None = None
    venv_path: str | None = None
    python_version: str | None = None

# File extensions commonly found in software projects.
_TEXT_EXTENSIONS = frozenset({
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".rst", ".txt", ".csv",
    ".java", ".kt", ".scala", ".c", ".cpp", ".h", ".hpp", ".cs",
    ".go", ".rs", ".rb", ".php", ".swift", ".r", ".sql",
    ".sh", ".bash", ".ps1", ".bat", ".cmd",
    ".xml", ".svg", ".env", ".gitignore", ".editorconfig",
    ".dockerfile", ".makefile",
})

# Directories to skip during scans (performance).
_SKIP_DIRS = frozenset({
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv",
    "venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "target", "bin", "obj", ".idea", ".vs",
})

MAX_RECENT = 10


class ProjectManager(QObject):
    """Manages the lifecycle of a user project.

    This class contains NO UI code.  It emits signals that UI components
    subscribe to.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_path: Path | None = None
        self._recent: list[str] = []
        self._scan_worker: BackgroundWorker | None = None

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def current_path(self) -> Path | None:
        """The currently open project root, or *None*."""
        return self._current_path

    @property
    def current_name(self) -> str:
        """Human-readable name of the current project."""
        if self._current_path is None:
            return "No Project"
        return self._current_path.name

    @property
    def recent_projects(self) -> list[str]:
        """List of recently opened project paths (most recent first)."""
        return list(self._recent)

    @recent_projects.setter
    def recent_projects(self, value: list[str]) -> None:
        self._recent = list(value)[:MAX_RECENT]

    # ── Actions ──────────────────────────────────────────────────────────

    def open_project(self, path: str | Path) -> bool:
        """Open a project at *path*.

        Returns ``True`` on success, ``False`` if validation fails.
        """
        path = Path(path).resolve()

        if not self._validate(path):
            return False

        # Close any existing project first.
        if self._current_path is not None:
            self.close_project()

        self._current_path = path
        LOG.info("Opening project: %s", path)

        # Update recent list.
        path_str = str(path)
        if path_str in self._recent:
            self._recent.remove(path_str)
        self._recent.insert(0, path_str)
        self._recent = self._recent[:MAX_RECENT]

        # Notify the system.
        signals.mission_update.emit("LOAD", f"Opening project: {path.name}")
        signals.project_opened.emit(str(path))
        signals.status_message.emit(f"Opened {path.name}")

        # Scan file statistics on a background thread.
        self._start_scan(path)
        return True

    def close_project(self) -> None:
        """Close the current project."""
        if self._current_path is None:
            return
        name = self._current_path.name
        self._current_path = None
        LOG.info("Closed project: %s", name)
        signals.project_closed.emit()
        signals.status_message.emit("Project closed")

    # ── Validation ───────────────────────────────────────────────────────

    @staticmethod
    def _validate(path: Path) -> bool:
        if not path.exists():
            LOG.warning("Path does not exist: %s", path)
            signals.mission_update.emit("ERROR", f"Path does not exist: {path}")
            return False
        if not path.is_dir():
            LOG.warning("Path is not a directory: %s", path)
            signals.mission_update.emit("ERROR", f"Not a directory: {path}")
            return False
        return True

    # ── Background scan ──────────────────────────────────────────────────

    def _start_scan(self, path: Path) -> None:
        """Scan the project for file statistics without blocking the UI."""
        signals.mission_update.emit("SCAN", "Scanning project files...")

        self._scan_worker = BackgroundWorker(self._count_files, path, parent=self)
        self._scan_worker.result_ready.connect(self._on_scan_complete)
        self._scan_worker.start()

    @staticmethod
    def _count_files(root: Path) -> int:
        """Walk the project tree and count files (excluding skip dirs)."""
        count = 0
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Modify dirnames in-place to prune skipped directories.
                dirnames[:] = [
                    d for d in dirnames
                    if d not in _SKIP_DIRS and not d.startswith(".")
                ]
                count += len(filenames)
        except OSError:
            pass
        return count

    def _on_scan_complete(self, result: object) -> None:
        if isinstance(result, int) and self._current_path is not None:
            name = self._current_path.name
            signals.project_stats.emit(name, result)
            signals.mission_update.emit("READY", f"Loaded {result} files")
            LOG.info("Project scan complete: %d files", result)
        self._scan_worker = None

    # ── Project creation (Milestone 4) ───────────────────────────────────

    def create_project(
        self, name: str, path: Path, template_id: str,
    ) -> Path:
        """Create a new project from a template and open it.

        Returns the project root path.
        """
        from friday_ai.services.project_templates import default_registry

        template = default_registry.get_template(template_id)
        if not template:
            LOG.error("Unknown template: %s", template_id)
            signals.mission_update.emit("ERROR", f"Unknown template: {template_id}")
            return path

        # Create directory
        path.mkdir(parents=True, exist_ok=True)
        LOG.info("Creating project '%s' at %s using template '%s'", name, path, template_id)
        signals.mission_update.emit("CREATE", f"Creating {name}...")

        # Generate files from template
        template.create(path)

        # Save project metadata
        import datetime
        metadata = ProjectMetadata(
            name=name,
            project_type=template.language.lower() if template.language else "unknown",
            created=datetime.datetime.now().isoformat(),
            main_file=self._guess_main_file(template_id),
        )
        self.save_metadata(path, metadata)

        signals.project_created.emit(str(path))
        LOG.info("Project created: %s", path)

        # Open the new project
        self.open_project(path)
        return path

    @staticmethod
    def _guess_main_file(template_id: str) -> str | None:
        """Return the conventional main file for a template."""
        return {
            "python": "main.py",
            "java": "src/Main.java",
            "c": "src/main.c",
            "cpp": "src/main.cpp",
            "node": "src/index.js",
        }.get(template_id)

    # ── Type detection (Milestone 4) ─────────────────────────────────────

    def detect_project_type(self, path: Path) -> ProjectType:
        """Auto-detect the project type from files present at *path*."""
        if not path.is_dir():
            return ProjectType.UNKNOWN

        # Check stored metadata first
        meta = self.get_metadata(path)
        if meta and meta.project_type != "unknown":
            try:
                return ProjectType(meta.project_type)
            except ValueError:
                pass

        # Heuristic: inspect top-level and src/ files
        indicators: dict[ProjectType, int] = {}
        check_files = list(path.iterdir())
        src_dir = path / "src"
        if src_dir.is_dir():
            check_files.extend(src_dir.iterdir())

        ext_map = {
            ".py": ProjectType.PYTHON,
            ".java": ProjectType.JAVA,
            ".c": ProjectType.C, ".h": ProjectType.C,
            ".cpp": ProjectType.CPP, ".cc": ProjectType.CPP,
            ".hpp": ProjectType.CPP,
            ".js": ProjectType.NODE, ".ts": ProjectType.NODE,
            ".rs": ProjectType.RUST,
        }
        config_map = {
            "setup.py": ProjectType.PYTHON,
            "pyproject.toml": ProjectType.PYTHON,
            "requirements.txt": ProjectType.PYTHON,
            "package.json": ProjectType.NODE,
            "Cargo.toml": ProjectType.RUST,
            "pom.xml": ProjectType.JAVA,
            "build.gradle": ProjectType.JAVA,
            "CMakeLists.txt": ProjectType.CPP,
        }

        for f in check_files:
            if f.is_file():
                ext = f.suffix.lower()
                if ext in ext_map:
                    pt = ext_map[ext]
                    indicators[pt] = indicators.get(pt, 0) + 1
                if f.name in config_map:
                    pt = config_map[f.name]
                    indicators[pt] = indicators.get(pt, 0) + 5  # Config files weigh more

        if not indicators:
            return ProjectType.UNKNOWN
        if len(indicators) > 1:
            # If dominant type has >70% of weight, use it; otherwise MIXED
            total = sum(indicators.values())
            best = max(indicators, key=indicators.get)  # type: ignore[arg-type]
            if indicators[best] / total > 0.7:
                return best
            return ProjectType.MIXED
        return next(iter(indicators))

    # ── Metadata persistence (Milestone 4) ───────────────────────────────

    def get_project_data_dir(self, path: Path) -> Path:
        """Get the isolated AppData storage directory for a specific project."""
        path_hash = hashlib.md5(str(path.resolve()).encode("utf-8")).hexdigest()
        pdir = ConfigManager().FRIDAY_DATA_DIR / "projects" / path_hash
        pdir.mkdir(parents=True, exist_ok=True)
        return pdir

    def get_metadata(self, path: Path) -> ProjectMetadata | None:
        """Read project metadata from AppData."""
        meta_file = self.get_project_data_dir(path) / "project.json"
        if not meta_file.exists():
            return None
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            return ProjectMetadata(**{k: v for k, v in data.items()
                                     if k in ProjectMetadata.__dataclass_fields__})
        except Exception as e:
            LOG.warning("Failed to read project metadata: %s", e)
            return None

    def save_metadata(self, path: Path, metadata: ProjectMetadata) -> None:
        """Write project metadata to AppData."""
        meta_file = self.get_project_data_dir(path) / "project.json"
        try:
            meta_file.write_text(
                json.dumps(asdict(metadata), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            LOG.info("Saved project metadata: %s", meta_file)
        except Exception as e:
            LOG.warning("Failed to save project metadata: %s", e)

