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
    db = SessionLocal()
    try:
        from app.db.models import WorkloadQueue, Task
        picking_queue = db.query(WorkloadQueue).filter(WorkloadQueue.warehouse_id == warehouse_id, WorkloadQueue.process_type == "PICKING").first()
        active_tasks = db.query(Task).filter(Task.warehouse_id == warehouse_id, Task.status == "PENDING", Task.process_type == "PICKING").count()
        vol = picking_queue.volume if picking_queue else 0
        return json.dumps({"outbound_queue": vol, "active_tasks": active_tasks, "process_type": "PICKING"})
    finally:
        db.close()

@tool
def get_inbound_status(warehouse_id: str) -> str:
    """Retrieve the inbound queue."""
    db = SessionLocal()
    try:
        from app.db.models import WorkloadQueue
        recv_queue = db.query(WorkloadQueue).filter(WorkloadQueue.warehouse_id == warehouse_id, WorkloadQueue.process_type == "RECEIVING").first()
        vol = recv_queue.volume if recv_queue else 0
        return json.dumps({"inbound_queue": vol, "process_type": "RECEIVING"})
    finally:
        db.close()

@tool
def run_labour_prediction(warehouse_id: str, workload: int, available_workers: int) -> str:
    """Run the ML model to predict required workers."""
    db = SessionLocal()
    try:
        workers = db.query(Worker).filter(Worker.warehouse_id == warehouse_id).all()
        exp_sum = 0
        skill_sum = 0
        count = len(workers)
        if count > 0:
            for w in workers:
                exp_sum += (w.experience_years or 0)
                skill_map = {"Beginner": 1.0, "Intermediate": 2.0, "Expert": 3.0}
                skill_sum += skill_map.get(w.skill_level, 1.5)
            avg_exp = exp_sum / count
            avg_skill = skill_sum / count
        else:
            avg_exp = 3.5
            avg_skill = 1.1

        req = MLPredictionRequest(
            warehouse_id=warehouse_id, shift=1, process_type="PICKING", workload_quantity=workload,
            number_of_orders=int(workload/5), number_of_items=workload, number_of_skus=int(workload*0.1),
            scheduled_workers=available_workers, available_workers=available_workers,
            average_worker_experience=avg_exp, average_worker_skill=avg_skill, equipment_available=0.9,
            current_queue=1200, warehouse_utilization=0.85, historical_productivity=400.0,
            distance_factor=1.0, task_complexity=1.0
        )
        pred = predict_labour_requirement(req)
        return json.dumps({"required_workers": pred, "avg_exp": round(avg_exp, 2), "avg_skill": round(avg_skill, 2)})
    finally:
        db.close()

@tool
def run_delay_prediction(warehouse_id: str, workload: int, available_workers: int) -> str:
    """Run the ML model to predict delay risk."""
    db = SessionLocal()
    try:
        workers = db.query(Worker).filter(Worker.warehouse_id == warehouse_id).all()
        exp_sum = 0
        skill_sum = 0
        count = len(workers)
        if count > 0:
            for w in workers:
                exp_sum += (w.experience_years or 0)
                skill_map = {"Beginner": 1.0, "Intermediate": 2.0, "Expert": 3.0}
                skill_sum += skill_map.get(w.skill_level, 1.5)
            avg_exp = exp_sum / count
            avg_skill = skill_sum / count
        else:
            avg_exp = 3.5
            avg_skill = 1.1

        req = MLPredictionRequest(
            warehouse_id=warehouse_id, shift=1, process_type="PICKING", workload_quantity=workload,
            number_of_orders=int(workload/5), number_of_items=workload, number_of_skus=int(workload*0.1),
            scheduled_workers=available_workers, available_workers=available_workers,
            average_worker_experience=avg_exp, average_worker_skill=avg_skill, equipment_available=0.9,
            current_queue=1200, warehouse_utilization=0.85, historical_productivity=400.0,
            distance_factor=1.0, task_complexity=1.0
        )
        status, prob = predict_delay_probability(req)
        return json.dumps({"delay_probability": prob, "status": status, "avg_exp": round(avg_exp, 2), "avg_skill": round(avg_skill, 2)})
    finally:
        db.close()

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

@tool
def send_worker_instruction(warehouse_id: str, worker_id: str, instruction: str) -> str:
    """Send an instruction to a specific worker. They will receive it as a notification and can reply."""
    db = SessionLocal()
    try:
        from app.db.models import Worker
        from app.services.notification_service import create_notification
        worker = db.query(Worker).filter(Worker.worker_id == worker_id).first()
        if not worker:
            return json.dumps({"error": f"Worker {worker_id} not found."})

        notif = create_notification(
            db,
            user_id=worker.user_id,
            type="manager.instruction",
            message=instruction,
            priority="high",
            requires_ack=True,
            ack_minutes=10,
            dedup_key=f"manager.instruction:{worker_id}:{abs(hash(instruction))}",
        )
        db.commit()
        return json.dumps({"status": f"Instruction sent to {worker_id}.", "notification_id": notif.id})
    finally:
        db.close()

@tool
def draft_notification(warehouse_id: str, recipient_id: int, message: str) -> str:
    """Draft a new notification for a user, adding it to the QUEUED state."""
    db = SessionLocal()
    try:
        from app.services.notification_service import create_notification
        notif = create_notification(
            db, user_id=recipient_id, type="AGENT_DRAFT", message=message,
            priority="medium", dedup_key=f"agent.draft:{recipient_id}:{abs(hash(message))}",
        )
        db.commit()
        return json.dumps({"status": "Drafted notification and queued for delivery.", "notification_id": notif.id})
    finally:
        db.close()

@tool
def propose_reassignment(warehouse_id: str, task_id: int, new_worker_id: str) -> str:
    """Propose task reassignment to manager for approval (Action Engine)."""
    db = SessionLocal()
    try:
        key = f"propose-reassign:{task_id}:{new_worker_id}"
        existing = db.query(AgentAction).filter(AgentAction.idempotency_key == key).first()
        if existing:
            return json.dumps({"status": "Proposal already pending.", "action_id": existing.id})
        action = AgentAction(
            agent_name="SupervisorAgent",
            warehouse_id=warehouse_id,
            trigger="Reassignment Required",
            tool_called="propose_reassignment",
            action_type="REASSIGN_TASK",
            action_payload={"task_id": task_id, "new_worker_id": new_worker_id or None},
            idempotency_key=key,
            recommendation=f"Reassign Task {task_id} to Worker {new_worker_id}",
            manager_approval="PENDING"
        )
        db.add(action)
        db.commit()
        return json.dumps({"status": "Proposal submitted to Action Engine for Manager Approval.", "action_id": action.id})
    finally:
        db.close()

@tool
def add_new_employee(warehouse_id: str, name: str, skill_level: str, experience_years: float, shift: int) -> str:
    """Add a new employee to the warehouse and calculate the new average skill level. Skill level must be Beginner, Intermediate, or Expert."""
    db = SessionLocal()
    try:
        from app.db.models import Worker
        import uuid
        
        # Add the new worker
        new_worker = Worker(
            worker_id=f"W-{uuid.uuid4().hex[:6].upper()}",
            name=name,
            warehouse_id=warehouse_id,
            skill_level=skill_level,
            experience_years=experience_years,
            assigned_zone="A",
            shift=shift,
            status="PRESENT"
        )
        db.add(new_worker)
        db.commit()
        
        # Calculate new averages
        workers = db.query(Worker).filter(Worker.warehouse_id == warehouse_id).all()
        exp_sum = 0
        skill_sum = 0
        count = len(workers)
        if count > 0:
            for w in workers:
                exp_sum += (w.experience_years or 0)
                skill_map = {"Beginner": 1.0, "Intermediate": 2.0, "Expert": 3.0}
                skill_sum += skill_map.get(w.skill_level, 1.5)
            avg_exp = exp_sum / count
            avg_skill = skill_sum / count
            
        return json.dumps({
            "status": "Employee added successfully",
            "worker_id": new_worker.worker_id,
            "new_average_skill": round(avg_skill, 2),
            "new_average_experience": round(avg_exp, 2)
        })
    finally:
        db.close()
