from events.models import NetworkEvent, EventType
from decisions.engine import DecisionEngine
from audit.logger import AuditLogger
from state.manager import StateManager
from typing import Dict, Any

class EventHandler:
    def __init__(self, state_manager: StateManager, decision_engine: DecisionEngine, audit_logger: AuditLogger):
        self.state_manager = state_manager
        self.decision_engine = decision_engine
        self.audit_logger = audit_logger

    def handle_event(self, event: NetworkEvent) -> Dict[str, Any]:
        result = {"event_id": event.event_id, "processed": True, "decisions": []}
        
        if event.type == EventType.WORKER_SHORTAGE:
            decision = self.decision_engine.evaluate_worker_shortage(event.warehouse_id)
            if decision:
                self.audit_logger.log_decision(
                    event=event.type.value,
                    warehouse=event.warehouse_id,
                    tools_called=["get_warehouse_state", "find_resource_surplus", "create_resource_allocation_plan"],
                    recommendation=f"Allocate {decision.recommended_actions[0].get('quantity')} workers from {decision.recommended_actions[0].get('source')}" if decision.recommended_actions else "No action possible",
                    reasoning=decision.reasoning,
                    status=decision.status
                )
                result["decisions"].append(decision.model_dump())
                
        # Other event types can be handled similarly
        return result
