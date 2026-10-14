from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class InspectionReport:
    inspector: str
    status: HealthStatus
    timestamp: float
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
