from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.schemas.all_schemas import MLTrainingRequest, MLTrainingResponse
from app.ml.trainer import train_demand_model, train_availability_model

router = APIRouter()

@router.post("/demand/train", response_model=MLTrainingResponse)
async def train_demand(request: MLTrainingRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    background_tasks.add_task(train_demand_model, db, request.sample_fraction)
    return {"message": "Demand model training started", "task_status": "Processing"}

@router.post("/availability/train", response_model=MLTrainingResponse)
async def train_availability(request: MLTrainingRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    background_tasks.add_task(train_availability_model, db, request.sample_fraction)
    return {"message": "Availability model training started", "task_status": "Processing"}
