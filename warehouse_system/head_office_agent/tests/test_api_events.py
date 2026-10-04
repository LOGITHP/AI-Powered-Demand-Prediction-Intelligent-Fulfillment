import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_event_endpoint_produces_recommendation():
    # First send a warehouse update to populate state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Update WH-A (shortage)
        await ac.post("/api/warehouse-update", json={
            "warehouse_id": "WH-A",
            "timestamp": "2026-10-04T00:00:00Z",
            "operational_state": {"orders": 100, "pending_orders": 50, "workers": 20, "capacity_utilization": 0.8},
            "predictions": {"workload": "HIGH", "workers_required": 28, "risk_score": 0.9},
            "alerts": []
        })
        # Update WH-B (surplus)
        await ac.post("/api/warehouse-update", json={
            "warehouse_id": "WH-B",
            "timestamp": "2026-10-04T00:00:00Z",
            "operational_state": {"orders": 10, "pending_orders": 5, "workers": 30, "capacity_utilization": 0.2},
            "predictions": {"workload": "LOW", "workers_required": 10, "risk_score": 0.1},
            "alerts": []
        })
        
        # Send worker shortage event
        resp = await ac.post("/api/events", json={
            "event_id": "test-evt-1",
            "type": "WORKER_SHORTAGE",
            "warehouse_id": "WH-A",
            "timestamp": "2026-10-04T00:00:00Z",
            "severity": "HIGH",
            "payload": {"shortage_amount": 8}
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendation"] is not None
    assert data["recommendation"]["type"] == "WORKER_ALLOCATION"
