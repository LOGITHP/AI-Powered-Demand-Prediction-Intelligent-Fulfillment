import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_approve_executes_and_is_idempotent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Populate state
        await ac.post("/api/warehouse-update", json={
            "warehouse_id": "WH-A",
            "timestamp": "2026-10-04T00:00:00Z",
            "operational_state": {"orders": 100, "pending_orders": 50, "workers": 20, "capacity_utilization": 0.8},
            "predictions": {"workload": "HIGH", "workers_required": 28, "risk_score": 0.9},
            "alerts": []
        })
        await ac.post("/api/warehouse-update", json={
            "warehouse_id": "WH-B",
            "timestamp": "2026-10-04T00:00:00Z",
            "operational_state": {"orders": 10, "pending_orders": 5, "workers": 30, "capacity_utilization": 0.2},
            "predictions": {"workload": "LOW", "workers_required": 10, "risk_score": 0.1},
            "alerts": []
        })
        
        # Send event to get a recommendation
        event_resp = await ac.post("/api/events", json={
            "event_id": "test-evt-2",
            "type": "WORKER_SHORTAGE",
            "warehouse_id": "WH-A",
            "timestamp": "2026-10-04T00:00:00Z",
            "severity": "HIGH",
            "payload": {"shortage_amount": 8}
        })
        assert event_resp.status_code == 200
        decision_id = event_resp.json()["decision_id"]
        
        # Approve the decision
        approve_resp = await ac.post("/api/approve", json={
            "decision_id": decision_id,
            "approved": True,
            "notes": "Looks good"
        })
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "APPROVED"
        assert approve_resp.json()["execution_result"]["status"] == "SUCCESS"
        
        # Approve again to check idempotency
        approve_again_resp = await ac.post("/api/approve", json={
            "decision_id": decision_id,
            "approved": True,
            "notes": "Looks good"
        })
        assert approve_again_resp.status_code == 200
        assert approve_again_resp.json()["message"] == "Decision already processed"
