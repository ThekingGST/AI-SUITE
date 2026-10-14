from __future__ import annotations

import json
import subprocess
import sys
import venv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PyQt5.QtCore import QObject

from friday_ai.core.signals import signals
from friday_ai.services.toolchain_manager import ToolchainManager, ToolchainInfo
from shared.logger import get_logger


LOG = get_logger("friday.environment")


class EnvironmentType(Enum):
    PYTHON_VENV = "python_venv"
    CONDA = "conda"
    NODE = "node"
    JAVA_SDK = "java_sdk"
    SYSTEM = "system"


@dataclass
class EnvironmentInfo:
    """A project environment — runtime-agnostic."""
    name: str
    env_type: EnvironmentType
    path: str
    interpreter_path: str
    version: str
    is_active: bool = False


@dataclass
class PackageInfo:
    """An installed package — language-agnostic."""
    name: str
    version: str
    latest_version: str | None = None


class EnvironmentManager(QObject):
    def __init__(self, toolchain: ToolchainManager, parent: QObject | None = None):
        super().__init__(parent)
        self._toolchain = toolchain
        self._active_environment: EnvironmentInfo | None = None

    # Environment lifecycle
    def create_environment(self, project_path: Path, env_type: EnvironmentType, runtime: ToolchainInfo | None = None) -> EnvironmentInfo | None:
        LOG.info(f"Creating environment of type {env_type} at {project_path}")
        
        if env_type == EnvironmentType.PYTHON_VENV:
            env_path = project_path / ".venv"
            try:
                # Use venv.create directly as requested
                venv.create(env_path, with_pip=True)
                
                # Determine interpreter path based on OS
                if sys.platform == "win32":
                    interpreter = env_path / "Scripts" / "python.exe"
                else:
                    interpreter = env_path / "bin" / "python"
                
                env_info = EnvironmentInfo(
                    name=".venv",
                    env_type=EnvironmentType.PYTHON_VENV,
                    path=str(env_path),
                    interpreter_path=str(interpreter),
                    version="Unknown", # Could fetch via subprocess if needed
                    is_active=False
                )
                
                signals.environment_created.emit(str(env_path))
                LOG.info(f"Successfully created python venv at {env_path}")
                return env_info
            except Exception as e:
                LOG.error(f"Failed to create python venv: {e}")
                return None
                
        elif env_type == EnvironmentType.NODE:
            # Placeholder for node environment creation
            LOG.warning("Node environment creation not fully implemented")
            return None
        else:
            LOG.warning(f"Unsupported environment type for creation: {env_type}")
            return None

    def activate_environment(self, env_path: str) -> bool:
        path = Path(env_path)
        if not path.exists():
            LOG.error(f"Environment path does not exist: {env_path}")
            return False

        # In a more complete implementation we would figure out the env_type
        # For now, let's assume Python VENV based on path structures
        interpreter_path = path / "Scripts" / "python.exe" if sys.platform == "win32" else path / "bin" / "python"
        
        if not interpreter_path.exists():
            LOG.error(f"Interpreter not found for environment: {env_path}")
            return False

        self._active_environment = EnvironmentInfo(
            name=path.name,
            env_type=EnvironmentType.PYTHON_VENV,
            path=str(path),
            interpreter_path=str(interpreter_path),
            version="Unknown",
            is_active=True
        )
        
        signals.environment_changed.emit(self._active_environment.name, self._active_environment.interpreter_path)
        LOG.info(f"Activated environment: {env_path}")
        return True

    def remove_environment(self, env_path: str) -> bool:
        path = Path(env_path)
        if not path.exists():
            LOG.error(f"Environment path does not exist: {env_path}")
            return False
            
        import shutil
        try:
            shutil.rmtree(path)
            signals.environment_removed.emit(str(path))
            LOG.info(f"Removed environment: {env_path}")
            
            if self._active_environment and self._active_environment.path == str(path):
                self._active_environment = None
                
            return True
        except Exception as e:
            LOG.error(f"Failed to remove environment: {e}")
            return False

    def get_active_environment(self) -> EnvironmentInfo | None:
        return self._active_environment

    # Project integration
    def detect_project_environment(self, project_path: Path) -> EnvironmentInfo | None:
        # Check project.json for stored environment
        from friday_ai.services.project_manager import ProjectManager
        metadata = ProjectManager().get_metadata(project_path)
        
        if metadata:
            try:
                stored_env = metadata.environment_path
                if stored_env:
                        stored_path = Path(stored_env)
                        if stored_path.is_absolute() and stored_path.exists():
                            env_path = stored_path
                        else:
                            env_path = project_path / stored_env
                            
                        if env_path.exists():
                            interpreter_path = env_path / "Scripts" / "python.exe" if sys.platform == "win32" else env_path / "bin" / "python"
                            return EnvironmentInfo(
                                name=env_path.name,
                                env_type=EnvironmentType.PYTHON_VENV,
                                path=str(env_path),
                                interpreter_path=str(interpreter_path),
                                version="Unknown"
                            )
            except Exception as e:
                LOG.error(f"Failed to read project.json: {e}")

        # Check for Python venv
        for venv_name in [".venv", "venv"]:
            venv_path = project_path / venv_name
            if (venv_path / "pyvenv.cfg").exists():
                interpreter_path = venv_path / "Scripts" / "python.exe" if sys.platform == "win32" else venv_path / "bin" / "python"
                return EnvironmentInfo(
                    name=venv_name,
                    env_type=EnvironmentType.PYTHON_VENV,
                    path=str(venv_path),
                    interpreter_path=str(interpreter_path),
                    version="Unknown"
                )

        # Check for Node
        node_modules = project_path / "node_modules"
        if node_modules.exists():
            return EnvironmentInfo(
                name="node_modules",
                env_type=EnvironmentType.NODE,
                path=str(node_modules),
                interpreter_path="", # Node uses system node typically unless nvm/fnm is used
                version="Unknown"
            )

        return None

    def get_interpreter_for_project(self, project_path: Path) -> str:
        # 1. Check if project has a detected environment
        env_info = self.detect_project_environment(project_path)
        if env_info and env_info.interpreter_path:
            return env_info.interpreter_path

        # 2. Fall back to first available Python from ToolchainManager
        toolchains = self._toolchain.get_toolchains(language="python")
        if toolchains:
            return toolchains[0].executable_path

        # 3. Final fallback: sys.executable
        return sys.executable

    def _get_interpreter_for_env(self, env_path: str | None) -> str:
        if env_path:
            path = Path(env_path)
            interpreter = path / "Scripts" / "python.exe" if sys.platform == "win32" else path / "bin" / "python"
            if interpreter.exists():
                return str(interpreter)
        
        if self._active_environment and self._active_environment.interpreter_path:
            return self._active_environment.interpreter_path
            
        return sys.executable

    # Package management
    def install_package(self, name: str, env_path: str | None = None) -> bool:
        interpreter = self._get_interpreter_for_env(env_path)
        LOG.info(f"Installing package {name} using interpreter {interpreter}")
        
        try:
            result = subprocess.run(
                [interpreter, "-m", "pip", "install", name],
                capture_output=True,
                text=True,
                check=True,
                creationflags=0x08000000
            )
            # Emit signal
            # Note: We'd ideally parse the actual installed version from pip output
            signals.package_installed.emit(name, "latest")
            return True
        except subprocess.CalledProcessError as e:
            LOG.error(f"Failed to install package {name}: {e.stderr}")
            return False

    def upgrade_package(self, name: str, env_path: str | None = None) -> bool:
        interpreter = self._get_interpreter_for_env(env_path)
        LOG.info(f"Upgrading package {name} using interpreter {interpreter}")
        
        try:
            result = subprocess.run(
                [interpreter, "-m", "pip", "install", "--upgrade", name],
                capture_output=True,
                text=True,
                check=True,
                creationflags=0x08000000
            )
            return True
        except subprocess.CalledProcessError as e:
            LOG.error(f"Failed to upgrade package {name}: {e.stderr}")
            return False

    def uninstall_package(self, name: str, env_path: str | None = None) -> bool:
        interpreter = self._get_interpreter_for_env(env_path)
        LOG.info(f"Uninstalling package {name} using interpreter {interpreter}")
        
        try:
            result = subprocess.run(
                [interpreter, "-m", "pip", "uninstall", "-y", name],
                capture_output=True,
                text=True,
                check=True,
                creationflags=0x08000000
            )
            return True
        except subprocess.CalledProcessError as e:
            LOG.error(f"Failed to uninstall package {name}: {e.stderr}")
            return False

    def list_packages(self, env_path: str | None = None) -> list[PackageInfo]:
        interpreter = self._get_interpreter_for_env(env_path)
        LOG.info(f"Listing packages using interpreter {interpreter}")
        
        try:
            result = subprocess.run(
                [interpreter, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=0x08000000
            )
            
            packages_data = json.loads(result.stdout)
            packages = []
            for item in packages_data:
                packages.append(PackageInfo(
                    name=item.get("name", ""),
                    version=item.get("version", "")
                ))
            return packages
        except subprocess.CalledProcessError as e:
            LOG.error(f"Failed to list packages: {e.stderr}")
            return []
        except json.JSONDecodeError as e:
            LOG.error(f"Failed to parse pip list output: {e}")
            return []
