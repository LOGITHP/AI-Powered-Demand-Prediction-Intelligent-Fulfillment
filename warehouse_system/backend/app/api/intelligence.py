from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import LaborStandard, PlanRun
from app.api.auth import get_current_user
from app.intelligence.forecasting import forecast, backtest, get_history
from app.intelligence.workforce import manpower_gap, get_labor_standards
from app.intelligence.assignment import plan_assignment, run_assignment

router = APIRouter()


def _require_manager(current_user):
    if current_user.role not in ["MANAGER", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Manager/Admin only")


class LaborStandardIn(BaseModel):
    process_type: str
    units_per_hour: float
    productive_hours_per_shift: float = 7.0
    absenteeism_rate: float = 0.08


@router.get("/forecast")
def get_forecast(process_type: str, days: int = 7,
                 current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Deterministic forecast: volume + task-hours for the next N days."""
    return forecast(db, current_user.warehouse_id or "WH-001", process_type, horizon_days=days)


@router.get("/forecast/backtest")
def get_backtest(process_type: str, days: int = 7,
                 current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Rolling-origin evaluation (WAPE/MAPE) of the forecasting baseline."""
    history = get_history(db, current_user.warehouse_id or "WH-001", process_type)
    return backtest(history, horizon=days)


@router.get("/workforce-gap")
def get_workforce_gap(shift: int = 1, use_forecast: bool = True,
                      current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Headcount required vs available per process for a shift ('need N more on evening pick')."""
    return manpower_gap(db, current_user.warehouse_id or "WH-001", shift, use_forecast)


@router.get("/labor-standards")
def list_labor_standards(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = get_labor_standards(db, current_user.warehouse_id or "WH-001")
    return [{
        "process_type": r.process_type,
        "units_per_hour": r.units_per_hour,
        "productive_hours_per_shift": r.productive_hours_per_shift,
        "absenteeism_rate": r.absenteeism_rate,
    } for r in rows.values()]


@router.put("/labor-standards")
def upsert_labor_standard(body: LaborStandardIn,
                          current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Managers review/tune the labor standards that drive manpower planning."""
    _require_manager(current_user)
    wh = current_user.warehouse_id or "WH-001"
    std = db.query(LaborStandard).filter(
        LaborStandard.warehouse_id == wh, LaborStandard.process_type == body.process_type
    ).first()
    if not std:
        std = LaborStandard(warehouse_id=wh, process_type=body.process_type)
        db.add(std)
    std.units_per_hour = body.units_per_hour
    std.productive_hours_per_shift = body.productive_hours_per_shift
    std.absenteeism_rate = body.absenteeism_rate
    db.commit()
    return {"status": "saved", "process_type": std.process_type, "units_per_hour": std.units_per_hour}


@router.get("/assignment/preview")
def preview_assignment(shift: Optional[int] = None,
                       current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Optimal task->worker plan WITH explanation, nothing written (human-in-the-loop)."""
    return plan_assignment(db, current_user.warehouse_id or "WH-001", shift)


@router.post("/assignment/run")
def execute_assignment(shift: Optional[int] = None,
                       current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Execute the previewed plan: assign tasks + notify workers (manager action)."""
    _require_manager(current_user)
    return run_assignment(db, current_user.warehouse_id or "WH-001", shift)


@router.get("/plan-runs")
def list_plan_runs(limit: int = 20, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Audit trail of planning pipeline executions (Planned vs Actual input)."""
    runs = (db.query(PlanRun).order_by(PlanRun.created_at.desc()).limit(limit).all())
    return [{
        "plan_id": r.plan_id, "instruction_id": r.instruction_id, "warehouse_id": r.warehouse_id,
        "status": r.status, "steps": r.steps, "created_at": r.created_at.isoformat(),
    } for r in runs]
