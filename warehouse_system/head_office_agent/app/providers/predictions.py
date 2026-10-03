from abc import ABC, abstractmethod
from typing import Dict, Any

class WorkloadPredictionProvider(ABC):
    @abstractmethod
    def predict(self, warehouse_id: str, operational_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

class WorkerRequirementProvider(ABC):
    @abstractmethod
    def predict(self, warehouse_id: str, operational_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

class RiskPredictionProvider(ABC):
    @abstractmethod
    def predict(self, warehouse_id: str, operational_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

class MockWorkerRequirementProvider(WorkerRequirementProvider):
    def predict(self, warehouse_id: str, operational_data: Dict[str, Any]) -> Dict[str, Any]:
        # Return a static mock prediction for testing
        return {
            "workers_required": 36,
            "confidence": 0.91
        }
