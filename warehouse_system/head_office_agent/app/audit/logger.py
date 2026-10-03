from typing import List, Dict, Any
from datetime import datetime

class AuditLogger:
    def __init__(self):
        self.logs = []

    def log_decision(self, event: str, warehouse: str, tools_called: List[str], recommendation: str, status: str, reasoning: List[str] = None):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "warehouse": warehouse,
            "tools_called": tools_called,
            "recommendation": recommendation,
            "reasoning": reasoning or [],
            "status": status
        }
        self.logs.append(log_entry)
        
    def get_logs(self) -> List[Dict[str, Any]]:
        return self.logs
