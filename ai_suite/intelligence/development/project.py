import time
import os
from pathlib import Path
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class ProjectInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "project"
        
    requires_args = True

    def inspect(self) -> InspectionReport:
        return self.inspect_with_args()

    def inspect_with_args(self, project_path: str = ".") -> InspectionReport:
        path = Path(project_path)
        if not path.exists() or not path.is_dir():
            return InspectionReport(
                inspector=self.name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                summary=f"Path not found: {project_path}"
            )
            
        markers = {
            "requirements.txt": "Python",
            "pyproject.toml": "Python",
            "package.json": "Node.js",
            "Cargo.toml": "Rust",
            "pom.xml": "Java",
            "go.mod": "Go"
        }
        
        detected_lang = "Unknown"
        for marker, lang in markers.items():
            if (path / marker).exists():
                detected_lang = lang
                break
                
        # Count files roughly
        file_count = 0
        for root, dirs, files in os.walk(str(path)):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
            file_count += len(files)
            
        return InspectionReport(
            inspector=self.name,
            status=HealthStatus.HEALTHY,
            timestamp=time.time(),
            summary=f"{detected_lang} project with ~{file_count} files.",
            details={
                "language": detected_lang,
                "path": str(path.resolve())
            },
            metrics={"file_count": float(file_count)}
        )
