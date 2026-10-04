from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db.database import get_db
from app.db.models import Worker
from app.api.auth import get_current_user
from app.core.config import settings
import uuid

router = APIRouter()

class WorkerCreate(BaseModel):
    name: str
    skill_level: str
    experience_years: float
    assigned_zone: Optional[str] = "A"
    shift: Optional[int] = 1

@router.get("/")
def get_workers(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    wh = settings.WAREHOUSE_ID
    return db.query(Worker).filter(Worker.warehouse_id == wh).all()

@router.post("/")
def add_worker(worker: WorkerCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    wh = settings.WAREHOUSE_ID
    new_worker = Worker(
        worker_id=f"W-{uuid.uuid4().hex[:6].upper()}",
        name=worker.name,
        warehouse_id=wh,
        skill_level=worker.skill_level,
        experience_years=worker.experience_years,
        assigned_zone=worker.assigned_zone,
        shift=worker.shift,
        status="PRESENT"
    )
    db.add(new_worker)
    db.commit()
    return {"status": "success", "worker_id": new_worker.worker_id}
