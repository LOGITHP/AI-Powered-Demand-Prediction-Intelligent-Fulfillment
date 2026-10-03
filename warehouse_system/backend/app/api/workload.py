from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import case
from app.db.database import get_db
from app.db.models import WorkloadQueue, Task, OperationalEvent
from app.api.auth import get_current_user
from app.schemas import WorkloadRequest

router = APIRouter()

PRIORITY_ORDER = case(
    (Task.priority == "URGENT", 4),
    (Task.priority == "HIGH", 3),
    (Task.priority == "NORMAL", 2),
    (Task.priority == "LOW", 1),
    else_=0,
)

@router.get("/")
def get_workload(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    workload = db.query(WorkloadQueue).filter(WorkloadQueue.warehouse_id == current_user.warehouse_id).all()
    return workload

@router.post("/inbound")
def add_inbound_workload(request: WorkloadRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["INBOUND", "MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized to add inbound workload")
        
    valid_processes = ["RECEIVING", "INSPECTION", "PUTAWAY"]
    if request.process_type not in valid_processes:
        raise HTTPException(status_code=400, detail=f"Invalid inbound process. Must be one of {valid_processes}")
        
    # Add to queue
    queue = db.query(WorkloadQueue).filter(WorkloadQueue.warehouse_id == current_user.warehouse_id, WorkloadQueue.process_type == request.process_type).first()
    if queue:
        queue.volume += request.volume
    else:
        queue = WorkloadQueue(warehouse_id=current_user.warehouse_id, process_type=request.process_type, volume=request.volume)
        db.add(queue)
        
    # Log event
    event = OperationalEvent(
        warehouse_id=current_user.warehouse_id,
        event_type="WORKLOAD_RECEIVED",
        description=f"Received {request.volume} units for {request.process_type}",
        details={"volume": request.volume, "process_type": request.process_type}
    )
    db.add(event)
    db.commit()
    return {"status": "success", "message": f"Added {request.volume} to {request.process_type} queue"}

@router.post("/outbound")
def add_outbound_workload(request: WorkloadRequest, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["OUTBOUND", "MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Not authorized to add outbound workload")
        
    valid_processes = ["PICKING", "PACKING", "DISPATCH"]
    if request.process_type not in valid_processes:
        raise HTTPException(status_code=400, detail=f"Invalid outbound process. Must be one of {valid_processes}")
        
    # Add to queue
    queue = db.query(WorkloadQueue).filter(WorkloadQueue.warehouse_id == current_user.warehouse_id, WorkloadQueue.process_type == request.process_type).first()
    if queue:
        queue.volume += request.volume
    else:
        queue = WorkloadQueue(warehouse_id=current_user.warehouse_id, process_type=request.process_type, volume=request.volume)
        db.add(queue)
        
    # Create corresponding tasks for simulation (1 task per 50 units)
    num_tasks = max(1, request.volume // 50)
    for i in range(num_tasks):
        task = Task(
            warehouse_id=current_user.warehouse_id,
            process_type=request.process_type,
            priority=request.priority,
            status="PENDING",
            instructions=f"{request.process_type} task for {request.volume // num_tasks} units"
        )
        db.add(task)
        
    # Log event
    event = OperationalEvent(
        warehouse_id=current_user.warehouse_id,
        event_type="WORKLOAD_RECEIVED",
        description=f"Received {request.volume} units for {request.process_type}",
        details={"volume": request.volume, "process_type": request.process_type}
    )
    db.add(event)
    db.commit()
    return {"status": "success", "message": f"Added {request.volume} to {request.process_type} queue and generated {num_tasks} tasks"}

@router.get("/tasks/next")
def get_next_task(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(
        Task.warehouse_id == current_user.warehouse_id,
        Task.status.in_(["PENDING", "PLANNED", "ASSIGNED"])
    ).order_by(
        PRIORITY_ORDER.desc(),
        Task.created_at.asc()
    ).first()
    
    if not task:
        return {"id": None}
        
    if task.status in ("PENDING", "PLANNED"):
        task.status = "ASSIGNED"
        from app.db.models import Worker
        worker = db.query(Worker).filter(Worker.user_id == current_user.id).first()
        if worker:
            task.assigned_worker_id = worker.worker_id
        from datetime import datetime
        task.assigned_at = datetime.utcnow()
        db.commit()
        
    return {
        "id": task.id,
        "type": task.process_type,
        "location": task.zone or "Warehouse Floor",
        "items": 50,
        "priority": task.priority,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "instructions": task.instructions
    }

@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.warehouse_id == current_user.warehouse_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.status = "COMPLETED"
    
    # Also reduce workload queue volume
    queue = db.query(WorkloadQueue).filter(WorkloadQueue.warehouse_id == current_user.warehouse_id, WorkloadQueue.process_type == task.process_type).first()
    if queue and queue.volume > 0:
        queue.volume = max(0, queue.volume - 50)
        
    db.commit()
    return {"status": "success"}
