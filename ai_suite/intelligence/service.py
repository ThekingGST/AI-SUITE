import time
from typing import Any
from .base import BaseInspector
from .types import InspectionReport, HealthStatus

class IntelligenceService:
    def __init__(self):
        self._inspectors: dict[str, BaseInspector] = {}
        self._bootstrapped = False

    def register(self, inspector: BaseInspector) -> None:
        self._inspectors[inspector.name] = inspector

    def inspect(self, name: str, **kwargs: Any) -> InspectionReport:
        if name not in self._inspectors:
            return InspectionReport(
                inspector=name,
                status=HealthStatus.UNKNOWN,
                timestamp=time.time(),
                summary=f"Inspector '{name}' not found."
            )
        try:
            # We allow passing kwargs to inspectors that need them (like git/project)
            if kwargs and hasattr(self._inspectors[name], "inspect_with_args"):
                return self._inspectors[name].inspect_with_args(**kwargs) # type: ignore
            return self._inspectors[name].inspect()
        except Exception as e:
            import traceback
            return InspectionReport(
                inspector=name,
                status=HealthStatus.CRITICAL,
                timestamp=time.time(),
                summary=f"Inspector crashed: {e}",
                details={"traceback": traceback.format_exc()}
            )

    def inspect_all(self) -> list[InspectionReport]:
        reports = []
        for name, inspector in self._inspectors.items():
            if not getattr(inspector, "requires_args", False):
                reports.append(self.inspect(name))
        return reports

    def get_system_summary(self) -> str:
        reports = self.inspect_all()
        lines = []
        for r in reports:
            lines.append(f"{r.inspector.upper()}: [{r.status.value.upper()}] {r.summary}")
        return "\n".join(lines)

    def health_check(self) -> dict[str, HealthStatus]:
        return {r.inspector: r.status for r in self.inspect_all()}
