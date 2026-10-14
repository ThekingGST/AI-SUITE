import time
import subprocess
from pathlib import Path
from ..base import BaseInspector
from ..types import InspectionReport, HealthStatus

class GitInspector(BaseInspector):
    @property
    def name(self) -> str:
        return "git"
        
    requires_args = True
    
    def inspect(self) -> InspectionReport:
        return self.inspect_with_args()

    def inspect_with_args(self, repo_path: str = ".") -> InspectionReport:
        path = Path(repo_path)
        if not (path / ".git").exists():
            return InspectionReport(
                inspector=self.name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                summary=f"Not a git repository: {repo_path}"
            )
            
        def run_git(*args):
            try:
                res = subprocess.run(
                    ["git", *args], cwd=str(path), capture_output=True, text=True, timeout=3, creationflags=0x08000000
                )
                return res.stdout.strip() if res.returncode == 0 else ""
            except Exception:
                return ""
                
        branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
        status_out = run_git("status", "--porcelain")
        commits = run_git("log", "-n", "3", "--oneline")
        remote = run_git("config", "--get", "remote.origin.url")
        
        changed = len([line for line in status_out.splitlines() if line.strip()])
        
        return InspectionReport(
            inspector=self.name,
            status=HealthStatus.HEALTHY,
            timestamp=time.time(),
            summary=f"Branch '{branch}' with {changed} uncommitted changes.",
            details={
                "branch": branch,
                "remote": remote,
                "changed_files": changed,
                "recent_commits": commits.splitlines()
            },
            metrics={"changed_files": float(changed)}
        )
