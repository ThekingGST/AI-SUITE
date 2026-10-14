from abc import ABC, abstractmethod
from .types import InspectionReport

class BaseInspector(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def inspect(self) -> InspectionReport: ...
