from abc import ABC, abstractmethod
from typing import Dict, Any, List

class OptimizationProvider(ABC):
    @abstractmethod
    def optimize_worker_allocation(self, network_state: Dict[str, Any], constraints: List[str]) -> Dict[str, Any]:
        pass

class MockOptimizationProvider(OptimizationProvider):
    def optimize_worker_allocation(self, network_state: Dict[str, Any], constraints: List[str]) -> Dict[str, Any]:
        # Simple deterministic mock
        return {
            "allocations": [
                {
                    "source": "WH-B",
                    "target": "WH-A",
                    "quantity": 7
                }
            ],
            "objective_value": "mock_value",
            "constraints_satisfied": True
        }
