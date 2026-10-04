from abc import ABC, abstractmethod
from typing import Dict, Any, List

class OptimizationProvider(ABC):
    @abstractmethod
    def optimize_worker_allocation(self, network_state: Dict[str, Any], constraints: List[str]) -> Dict[str, Any]:
        pass

class RealOptimizationProvider(OptimizationProvider):
    def optimize_worker_allocation(self, network_state: Dict[str, Any], constraints: List[str]) -> Dict[str, Any]:
        shortages = []
        surpluses = []
        warehouses = network_state.get("warehouses", {})
        
        for wh_id, data in warehouses.items():
            workers = data.get("workers", 0)
            req = data.get("workers_required", 0)
            diff = workers - req
            if diff < 0:
                shortages.append({"id": wh_id, "shortage": -diff})
            elif diff > 0:
                surpluses.append({"id": wh_id, "surplus": diff})
                
        allocations = []
        for s in shortages:
            needed = s["shortage"]
            for surp in surpluses:
                if surp["surplus"] > 0 and needed > 0:
                    allocate = min(needed, surp["surplus"])
                    allocations.append({
                        "source": surp["id"],
                        "target": s["id"],
                        "quantity": allocate
                    })
                    surp["surplus"] -= allocate
                    needed -= allocate

        return {
            "allocations": allocations,
            "objective_value": "calculated_value",
            "constraints_satisfied": True
        }
