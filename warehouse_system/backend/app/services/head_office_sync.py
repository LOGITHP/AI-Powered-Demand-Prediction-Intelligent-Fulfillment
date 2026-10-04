"""
Pushes a snapshot of this warehouse's operational state to the Head Office
agent so it can reason over the whole network.

The Head Office API is unauthenticated (internal network) and expects a
WarehouseUpdate: {warehouse_id, timestamp, operational_state, predictions}.
"""
import logging
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import InboundShipment, StorageLocation, Worker, WorkerPresence, WorkloadQueue
from app.ml.services import predict_delay_probability, predict_labour_requirement
from app.schemas import MLPredictionRequest

logger = logging.getLogger(__name__)

SYNC_TIMEOUT = 10  # seconds


def _collect_snapshot(db: Session, warehouse_id: str) -> dict:
    present = (
        db.query(WorkerPresence)
        .filter(WorkerPresence.warehouse_id == warehouse_id, WorkerPresence.status == "PRESENT")
        .count()
    )
    scheduled = db.query(Worker).filter(Worker.warehouse_id == warehouse_id).count()

    active_inbound = (
        db.query(InboundShipment)
        .filter(InboundShipment.warehouse_id == warehouse_id,
                InboundShipment.status.in_(["EXPECTED", "ARRIVED", "RECEIVING", "INSPECTION", "PUTAWAY"]))
        .count()
    )
    pending_inbound = (
        db.query(InboundShipment)
        .filter(InboundShipment.warehouse_id == warehouse_id,
                InboundShipment.status.in_(["EXPECTED", "ARRIVED"]))
        .count()
    )

    queue_rows = (
        db.query(WorkloadQueue.volume)
        .filter(WorkloadQueue.warehouse_id == warehouse_id)
        .all()
    )
    total_volume = sum(v or 0 for (v,) in queue_rows)

    # Capacity utilization from storage occupancy when available
    occupancy = (
        db.query(StorageLocation)
        .filter(StorageLocation.warehouse_id == warehouse_id)
        .with_entities(StorageLocation.capacity, StorageLocation.current_occupancy)
        .all()
    )
    if occupancy:
        capacity = sum(c or 0 for c, _ in occupancy)
        used = sum(o or 0 for _, o in occupancy)
        utilization = round(used / capacity, 3) if capacity else 0.0
    else:
        utilization = min(0.95, round(total_volume / 5000, 3)) if total_volume else 0.2

    workload = total_volume + active_inbound * 50
    workers_data = db.query(Worker).filter(Worker.warehouse_id == warehouse_id).all()
    avg_skill = 1.1
    avg_exp = 3.5
    if workers_data:
        skill_map = {"BEGINNER": 0.8, "INTERMEDIATE": 1.1, "EXPERT": 1.5}
        total_skill = sum(skill_map.get(w.skill_level.upper(), 1.0) if w.skill_level else 1.0 for w in workers_data)
        total_exp = sum(w.experience_years or 0.0 for w in workers_data)
        avg_skill = total_skill / len(workers_data)
        avg_exp = total_exp / len(workers_data)

    try:
        ml_req = MLPredictionRequest(
            warehouse_id=warehouse_id, shift=1, process_type="PICKING",
            workload_quantity=workload or 100,
            number_of_orders=max(1, active_inbound), number_of_items=workload or 100,
            number_of_skus=max(1, int((workload or 100) * 0.1)),
            scheduled_workers=max(1, scheduled), available_workers=max(1, present),
            average_worker_experience=avg_exp, average_worker_skill=avg_skill,
            equipment_available=0.9, current_queue=total_volume,
            warehouse_utilization=utilization, historical_productivity=400.0,
            distance_factor=1.0, task_complexity=1.0,
        )
        workers_required = int(predict_labour_requirement(ml_req))
        delay_status, delay_prob = predict_delay_probability(ml_req)
        risk_score = round(float(delay_prob or 0), 3)
        workload_level = "HIGH" if risk_score > 0.6 else ("MEDIUM" if total_volume > 1000 else "LOW")
    except Exception:
        logger.exception("ML prediction failed during sync; using worker-based estimate")
        workers_required = max(1, scheduled)
        risk_score = round(min(0.9, utilization), 3)
        workload_level = "HIGH" if utilization > 0.85 else ("MEDIUM" if utilization > 0.6 else "LOW")

    return {
        "warehouse_id": warehouse_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operational_state": {
            "orders": active_inbound,
            "pending_orders": pending_inbound,
            "workers": present,
            "capacity_utilization": utilization,
        },
        "predictions": {
            "workload": workload_level,
            "workers_required": workers_required,
            "risk_score": risk_score,
        },
        "alerts": [],
    }


def sync_warehouse_status_to_head_office(db: Session, warehouse_id: str = settings.WAREHOUSE_ID) -> bool:
    base_url = settings.HEAD_OFFICE_BASE_URL.rstrip("/")
    try:
        payload = _collect_snapshot(db, warehouse_id)
        res = requests.post(f"{base_url}/warehouse-update", json=payload, timeout=SYNC_TIMEOUT)
        if res.status_code == 200:
            logger.info("Synced %s to Head Office (risk=%.2f, workers=%d/%d)",
                        warehouse_id, payload["predictions"]["risk_score"],
                        payload["operational_state"]["workers"],
                        payload["predictions"]["workers_required"])
            return True
        logger.error("Head Office sync failed [%s]: %s", res.status_code, res.text[:300])
    except Exception as e:
        logger.error("Error syncing with head office at %s: %s", base_url, e)
    return False
