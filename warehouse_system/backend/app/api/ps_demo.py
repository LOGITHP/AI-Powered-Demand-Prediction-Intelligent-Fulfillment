from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Notification, User
from datetime import datetime
import random

router = APIRouter()

@router.get("/forecasting")
def get_forecasting_data():
    return {
        "inbound": {
            "predicted": "12,450", "hist_avg": "10,200", "current": "10,800", "change_pct": 22.1,
            "chart": [
                {"time": "08:00", "historical": 120, "predicted": 150},
                {"time": "10:00", "historical": 180, "predicted": 220},
                {"time": "12:00", "historical": 300, "predicted": 380},
                {"time": "14:00", "historical": 250, "predicted": 310},
                {"time": "16:00", "historical": 200, "predicted": 240},
                {"time": "18:00", "historical": 150, "predicted": 190}
            ]
        },
        "outbound": {
            "predicted": "9,850", "hist_avg": "9,100", "current": "9,500", "change_pct": 8.2,
            "chart": [
                {"time": "08:00", "historical": 100, "predicted": 110},
                {"time": "10:00", "historical": 150, "predicted": 160},
                {"time": "12:00", "historical": 250, "predicted": 270},
                {"time": "14:00", "historical": 300, "predicted": 350},
                {"time": "16:00", "historical": 280, "predicted": 310},
                {"time": "18:00", "historical": 200, "predicted": 230}
            ]
        },
        "inventory": {
            "current": "45,200", "predicted_move": "15,800", "expected_change": "+2,600",
            "chart": [
                {"time": "Mon", "inbound": 2400, "outbound": 2100, "net": 300, "predicted": 500},
                {"time": "Tue", "inbound": 2200, "outbound": 2300, "net": -100, "predicted": -50},
                {"time": "Wed", "inbound": 3100, "outbound": 2500, "net": 600, "predicted": 750},
                {"time": "Thu", "inbound": 2800, "outbound": 2900, "net": -100, "predicted": 0},
                {"time": "Fri", "inbound": 3500, "outbound": 3100, "net": 400, "predicted": 600}
            ]
        },
        "workload": {
            "current": "8,500 units/hr", "forecast": "11,200 units/hr", "inbound": "5,800", "outbound": "5,400", "peak": "14:00 - 16:00", "workers": "145",
            "chart": [
                {"time": "06:00", "actual": 2000, "forecast": 2100},
                {"time": "09:00", "actual": 4500, "forecast": 4800},
                {"time": "12:00", "actual": 8500, "forecast": 9200},
                {"time": "15:00", "actual": 10500, "forecast": 11200},
                {"time": "18:00", "actual": None, "forecast": 7500},
                {"time": "21:00", "actual": None, "forecast": 3200}
            ]
        }
    }

@router.get("/workforce")
def get_workforce_data(db: Session = Depends(get_db)):
    from app.db.models import Worker, Task
    
    # Get actual workers from DB
    workers = db.query(Worker).all()
    
    # Get active tasks
    active_tasks = db.query(Task).filter(Task.status.in_(["PENDING", "IN_PROGRESS"])).all()
    task_map = {t.assigned_worker_id: f"{t.process_type} - {t.instructions}" for t in active_tasks if t.assigned_worker_id}
    
    shifts_data = []
    active_count = 0
    for w in workers:
        if w.status == "ON_SHIFT":
            active_count += 1
        
        # Only show a subset or all depending on requirement; let's show all or maybe just a few if too many.
        # But user wants to see actual logged in people. Let's just return all workers, or maybe only ON_SHIFT + some scheduled.
        # We will return up to 20 workers for UI sanity, prioritizing ON_SHIFT.
        if len(shifts_data) < 20 or w.status == "ON_SHIFT":
            shift_name = "Morning" if w.shift == 1 else "Afternoon" if w.shift == 2 else "Night"
            shifts_data.append({
                "worker": f"{w.worker_id} ({w.name})",
                "shift": shift_name,
                "zone": w.assigned_zone or "Unassigned",
                "skill": w.skill_level or "General",
                "status": "Active" if w.status == "ON_SHIFT" else "Scheduled" if w.status == "OFF_SHIFT" else w.status,
                "assignment": task_map.get(w.worker_id, "Idle")
            })
            
    # Sort so Active is first
    shifts_data.sort(key=lambda x: 0 if x["status"] == "Active" else 1)

    return {
        "manpower": { "required": 145, "available": active_count, "shortage": max(0, 145 - active_count), "surplus": max(0, active_count - 145) },
        "recommendation": { "recommended": 150, "current": active_count, "required": 145, "gap": active_count - 145, "action": "Reallocate workers based on active tasks." },
        "shifts": shifts_data[:50], # Send up to 50
        "allocation": [
            {"process": "Receiving", "required": 20, "available": 22, "diff": 2, "status": "OVERSTAFFED"},
            {"process": "Putaway", "required": 25, "available": 25, "diff": 0, "status": "BALANCED"},
            {"process": "Picking", "required": 65, "available": 55, "diff": -10, "status": "UNDERSTAFFED"},
            {"process": "Packing", "required": 35, "available": 30, "diff": -5, "status": "UNDERSTAFFED"}
        ],
        "demand_chart": [
            {"time": "08:00", "workload": 80, "capacity": 100},
            {"time": "10:00", "workload": 120, "capacity": 110},
            {"time": "12:00", "workload": 150, "capacity": 130},
            {"time": "14:00", "workload": 180, "capacity": 140},
            {"time": "16:00", "workload": 160, "capacity": 140},
            {"time": "18:00", "workload": 90, "capacity": 100}
        ]
    }

@router.get("/analytics")
def get_analytics_data():
    return {
        "kpis": [
            {"name": "Order Fulfillment Rate", "actual": "98.5%", "benchmark": "98.0%", "variance": "+0.5%", "status": "GOOD"},
            {"name": "Dock-to-Stock Time", "actual": "2.4 hrs", "benchmark": "3.0 hrs", "variance": "-0.6 hrs", "status": "GOOD"},
            {"name": "Picking Accuracy", "actual": "99.1%", "benchmark": "99.5%", "variance": "-0.4%", "status": "WARNING"}
        ],
        "inbound": {
            "throughput": 450, "receiving_ct": 12, "inspection_ct": 8, "putaway_ct": 15, "queue": 120, "utilization": 85,
            "chart": [
                {"time": "08:00", "throughput": 200}, {"time": "10:00", "throughput": 350},
                {"time": "12:00", "throughput": 450}, {"time": "14:00", "throughput": 400},
                {"time": "16:00", "throughput": 300}, {"time": "18:00", "throughput": 150}
            ]
        },
        "outbound": {
            "picking_tp": 650, "packing_tp": 620, "loading_tp": 600, "picking_ct": 5, "packing_ct": 3, "queue": 85, "utilization": 92,
            "chart": [
                {"time": "08:00", "throughput": 300}, {"time": "10:00", "throughput": 450},
                {"time": "12:00", "throughput": 650}, {"time": "14:00", "throughput": 750},
                {"time": "16:00", "throughput": 600}, {"time": "18:00", "throughput": 400}
            ]
        },
        "inventory": {
            "movement": "15,400", "utilization": 88, "inbound": "8,200", "outbound": "7,200", "change": "+1,000", "trend": "Increasing"
        },
        "insights": {
            "observation": "Picking accuracy has dropped to 99.1% during peak hours (14:00 - 16:00).",
            "evidence": "Error logs show 45 mispicks in Zone B, which is currently operating at 98% utilization.",
            "factors": "High worker fatigue, dense order clustering, and insufficient temporary staging space.",
            "recommendation": "Deploy 3 additional workers to Zone B during 14:00-16:00 and enable dynamic batching algorithm."
        }
    }

@router.get("/optimization")
def get_optimization_data(scenario: str = "0"):
    peak_mod = 1.0 + (int(scenario) / 100.0)
    
    return {
        "underutilized": [
            {"area": "Receiving Dock 3", "workload": int(200 * peak_mod), "capacity": 300, "utilization": int(66 * peak_mod), "surplus": 2},
            {"area": "Putaway Zone A", "workload": int(150 * peak_mod), "capacity": 250, "utilization": int(60 * peak_mod), "surplus": 3}
        ],
        "overutilized": [
            {"area": "Picking Zone B", "workload": int(850 * peak_mod), "capacity": 700, "shortage": int(4 * peak_mod), "risk": int(15 * peak_mod)},
            {"area": "Packing Station 1", "workload": int(600 * peak_mod), "capacity": 500, "shortage": int(2 * peak_mod), "risk": int(12 * peak_mod)}
        ],
        "redistribution": {
            "source": "Putaway Zone A", "destination": "Picking Zone B", "workers": 3, "reason": "Zone A has 60% utilization while Zone B is exceeding capacity.", "status": "Pending Approval"
        },
        "accuracy": {
            "predicted": 145, "actual": 142, "error": "-3", "pct": 97.9,
            "chart": [
                {"time": "Mon", "predicted": 120, "actual": 118},
                {"time": "Tue", "predicted": 125, "actual": 128},
                {"time": "Wed", "predicted": 135, "actual": 132},
                {"time": "Thu", "predicted": 140, "actual": 140},
                {"time": "Fri", "predicted": 145, "actual": 142}
            ]
        },
        "scenario": {
            "current": {
                "workload": 12500, "workers": 145, "available": 132, "time": 45
            },
            "simulated": {
                "workload": int(12500 * peak_mod), "workers": int(145 * peak_mod), "diff": 132 - int(145 * peak_mod), "time": int(45 * peak_mod), "risk": max(0, int((peak_mod - 1.0) * 50))
            }
        }
    }

@router.post("/optimization/approve")
def approve_optimization(db: Session = Depends(get_db)):
    from app.db.models import Worker, Notification
    from datetime import datetime
    
    # Find 3 workers currently in Putaway_A
    workers_to_move = db.query(Worker).filter(Worker.assigned_zone == 'Putaway_A').limit(3).all()
    
    # If not enough, fallback to any workers
    if not workers_to_move:
        workers_to_move = db.query(Worker).limit(3).all()
        
    for worker in workers_to_move:
        # Reassign them in DB
        worker.assigned_zone = 'Picking_B'
        
        # Send notification
        new_notif = Notification(
            user_id=worker.user_id,
            message=f"ACTION REQUIRED: Workforce redistribution approved. Move to Picking Zone B immediately.",
            type="INSTRUCTION",
            status="QUEUED"
        )
        db.add(new_notif)
        
    db.commit()
    
    worker_ids = ", ".join([w.worker_id for w in workers_to_move])
    return {"status": "success", "message": f"Redistribution approved. Workers notified: {worker_ids}"}
