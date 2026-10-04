from typing import List, Dict, Any, Optional
from datetime import datetime

class AuditLogger:
    def __init__(self):
        self.logs = []

    def log_decision(self, event: str, warehouse: str, tools_called: List[str],
                     recommendation: str, status: str, reasoning: List[str] = None,
                     decision_id: Optional[str] = None):
        log_entry = {
            "decision_id": decision_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "warehouse": warehouse,
            "tools_called": tools_called,
            "recommendation": recommendation,
            "reasoning": reasoning or [],
            "status": status
        }
        self.logs.append(log_entry)
        # Keep memory bounded; recent decisions matter most for approval flows
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]

    def get_logs(self) -> List[Dict[str, Any]]:
        return list(reversed(self.logs))  # newest first

    def get_pending_decisions(self) -> List[Dict[str, Any]]:
        return [l for l in self.logs if l.get("status") == "PENDING_APPROVAL"]

    def resolve_decision(self, decision_id: str, status: str) -> Optional[Dict[str, Any]]:
        for entry in self.logs:
            if entry.get("decision_id") == decision_id:
                entry["status"] = status
                entry["resolved_at"] = datetime.utcnow().isoformat()
                return entry
        return None
