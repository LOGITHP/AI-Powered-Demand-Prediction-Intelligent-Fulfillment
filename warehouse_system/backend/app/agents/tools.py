import json
from langchain_core.tools import tool
from app.db.database import SessionLocal
from app.db.models import Worker, WorkerPresence, Task, Notification, AgentAction
from app.ml.services import predict_labour_requirement, predict_delay_probability, predict_congestion_probability
from app.schemas import MLPredictionRequest

@tool
def get_warehouse_status(warehouse_id: str) -> str:
    """Retrieve the general status of the warehouse."""
    # In a real system, aggregate actual DB rows. Here we simulate the query.
    return json.dumps({"warehouse_id": warehouse_id, "utilization": 0.85, "equipment_available": 0.92})

@tool
def get_worker_status(warehouse_id: str) -> str:
    """Retrieve the counts of present and absent workers."""
    db = SessionLocal()
    try:
        present = db.query(WorkerPresence).filter(WorkerPresence.warehouse_id == warehouse_id, WorkerPresence.status == "PRESENT").count()
        scheduled = db.query(Worker).filter(Worker.warehouse_id == warehouse_id, Worker.shift == 1).count() # simplify to shift 1
        return json.dumps({"present_workers": present, "scheduled_workers": scheduled, "absent_workers": scheduled - present})
    finally:
        db.close()

@tool
def get_outbound_status(warehouse_id: str) -> str:
    """Retrieve the outbound queue and active tasks."""
    return json.dumps({"outbound_queue": 8400, "active_tasks": 12, "process_type": "PICKING"})

@tool
def run_labour_prediction(warehouse_id: str, workload: int, available_workers: int) -> str:
    """Run the ML model to predict required workers."""
    req = MLPredictionRequest(
        warehouse_id=warehouse_id, shift=1, process_type="PICKING", workload_quantity=workload,
        number_of_orders=int(workload/5), number_of_items=workload, number_of_skus=int(workload*0.1),
        scheduled_workers=available_workers, available_workers=available_workers,
        average_worker_experience=3.5, average_worker_skill=1.1, equipment_available=0.9,
        current_queue=1200, warehouse_utilization=0.85, historical_productivity=400.0,
        distance_factor=1.0, task_complexity=1.0
    )
    pred = predict_labour_requirement(req)
    return json.dumps({"required_workers": pred})

@tool
def run_delay_prediction(warehouse_id: str, workload: int, available_workers: int) -> str:
    """Run the ML model to predict delay risk."""
    req = MLPredictionRequest(
        warehouse_id=warehouse_id, shift=1, process_type="PICKING", workload_quantity=workload,
        number_of_orders=int(workload/5), number_of_items=workload, number_of_skus=int(workload*0.1),
        scheduled_workers=available_workers, available_workers=available_workers,
        average_worker_experience=3.5, average_worker_skill=1.1, equipment_available=0.9,
        current_queue=1200, warehouse_utilization=0.85, historical_productivity=400.0,
        distance_factor=1.0, task_complexity=1.0
    )
    status, prob = predict_delay_probability(req)
    return json.dumps({"delay_probability": prob, "status": status})

@tool
def recommend_worker_redistribution(warehouse_id: str, shortage: int, from_zone: str, to_zone: str) -> str:
    """Generate a recommendation to redistribute workers. Requires manager approval."""
    rec = f"Reassign {shortage} eligible workers from {from_zone} to {to_zone}."
    return json.dumps({"recommendation": rec, "action_required": "MANAGER_APPROVAL"})

@tool
def request_manager_approval(warehouse_id: str, action_description: str) -> str:
    """Log an approval request for the manager."""
    db = SessionLocal()
    try:
        action = AgentAction(
            agent_name="WarehouseAgent",
            warehouse_id=warehouse_id,
            recommendation=action_description,
            manager_approval="PENDING"
        )
        db.add(action)
        db.commit()
        return json.dumps({"status": "Awaiting Manager Approval"})
    finally:
        db.close()
