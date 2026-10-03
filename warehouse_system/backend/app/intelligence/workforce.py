"""
Smart Workforce Planning (deterministic).

required_hours = volume / labor_standard_units_per_hour
required_headcount = ceil(required_hours / productive_hours_per_shift / (1 - absenteeism_rate))
gap = required_headcount - available_workers(per process + shift)

Workers are matched to a process by their assigned_zone, which matches the
process type names in this system (RECEIVING, INSPECTION, PUTAWAY, PICKING,
PACKING, DISPATCH).
"""
import math
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    LaborStandard, WorkloadQueue, Worker, WorkerPresence, VolumeHistory,
)
from app.intelligence.forecasting import seasonal_naive, get_history

DEFAULT_UPH = 50.0


def get_labor_standards(db: Session, warehouse_id: str) -> dict:
    rows = db.query(LaborStandard).filter(LaborStandard.warehouse_id == warehouse_id).all()
    return {r.process_type: r for r in rows}


def required_hours_for_volume(volume: float, units_per_hour: float) -> float:
    return volume / units_per_hour if units_per_hour > 0 else 0.0


def headcount_needed(volume: float, standard: LaborStandard) -> int:
    hours = required_hours_for_volume(volume, standard.units_per_hour)
    productive = max(standard.productive_hours_per_shift or 7.0, 1.0)
    absenteeism = min(max(standard.absenteeism_rate or 0.0, 0.0), 0.5)
    return math.ceil(hours / productive / (1.0 - absenteeism))


def available_workers_by_process(db: Session, warehouse_id: str, shift: int) -> dict:
    """Workers currently on shift for the given shift number, grouped by zone (process)."""
    workers = (
        db.query(Worker)
        .filter(
            Worker.warehouse_id == warehouse_id,
            Worker.shift == shift,
            Worker.status == "ON_SHIFT",
        )
        .all()
    )
    grouped = {}
    for w in workers:
        grouped.setdefault(w.assigned_zone, []).append(w)
    return grouped


def manpower_gap(db: Session, warehouse_id: str, shift: int, use_forecast: bool = True) -> dict:
    """
    Per-process manpower requirement vs availability for a shift.

    Volume source: next-day forecast (if use_forecast and history exists),
    else the live WorkloadQueue volume.
    """
    standards = get_labor_standards(db, warehouse_id)
    available = available_workers_by_process(db, warehouse_id, shift)

    process_types = sorted(set(list(standards.keys()) + list(available.keys()) +
                               [p for p in ("RECEIVING", "INSPECTION", "PUTAWAY", "PICKING", "PACKING", "DISPATCH")]))
    rows = []
    total_gap = 0
    for ptype in process_types:
        std = standards.get(ptype)
        uph = std.units_per_hour if std else DEFAULT_UPH

        volume = None
        source = "queue"
        if use_forecast:
            history = [v for _, v in get_history(db, warehouse_id, ptype)]
            if len(history) >= 7:
                volume = seasonal_naive(history, 1)[0]
                source = "forecast"
        if volume is None:
            queue = (
                db.query(WorkloadQueue)
                .filter(WorkloadQueue.warehouse_id == warehouse_id, WorkloadQueue.process_type == ptype)
                .first()
            )
            volume = queue.volume if queue else 0
            source = "queue"

        if std:
            needed = headcount_needed(volume, std)
        else:
            needed = math.ceil(required_hours_for_volume(volume, uph) / 7.0)

        have = len(available.get(ptype, []))
        gap = needed - have
        total_gap += max(0, gap)
        rows.append({
            "process_type": ptype,
            "shift": shift,
            "volume_source": source,
            "planned_volume": round(volume, 1),
            "units_per_hour": uph,
            "required_hours": round(required_hours_for_volume(volume, uph), 2),
            "required_headcount": needed,
            "available_workers": have,
            "gap": gap,
            "status": "SHORT" if gap > 0 else ("SURPLUS" if gap < -1 else "OK"),
        })

    message = None
    worst = max((r for r in rows if r["gap"] > 0), key=lambda r: r["gap"], default=None)
    if worst:
        message = (f"Need {worst['gap']} additional worker(s) for {worst['process_type']} "
                   f"on shift {shift} (planned volume {worst['planned_volume']}, "
                   f"{worst['units_per_hour']}/hr standard).")

    return {
        "warehouse_id": warehouse_id,
        "shift": shift,
        "generated_at": datetime.utcnow().isoformat(),
        "total_additional_workers_needed": total_gap,
        "summary": message or "Workforce is balanced for this shift.",
        "processes": rows,
    }
