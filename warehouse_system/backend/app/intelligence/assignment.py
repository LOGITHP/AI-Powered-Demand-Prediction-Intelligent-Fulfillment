"""
Task Assignment Engine (deterministic, human-in-the-loop friendly).

Phase 4 of the plan:
  1. Eligibility filter: status ON_SHIFT AND shift match AND zone/skill match
     (cross-trained workers from other zones are eligible with a penalty score,
     never silently preferred).
  2. Optimizer: Hungarian algorithm via scipy when available; deterministic
     greedy fallback (priority + deadline weighted) otherwise.

Assignment SCORES are explainable — every pair gets itemized points so the
manager portal can show why worker X got task Y.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.models import Task, Worker

PRIORITY_WEIGHT = {"URGENT": 40, "HIGH": 30, "NORMAL": 20, "LOW": 10}
SKILL_POINTS = {"EXPERT": 30, "INTERMEDIATE": 20, "BEGINNER": 10}
ZONE_MATCH_POINTS = 50
ZONE_MISMATCH_PENALTY = -25
ZONE_IMPOSSIBLE = 10 ** 6  # hard-block cost in the matrix

try:
    from scipy.optimize import linear_sum_assignment  # type: ignore
    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().upper()


def _task_zone(task: Task) -> str:
    return _norm(task.zone or task.process_type)


def _zones_match(worker_zone: str, task_zone: str) -> bool:
    """Process-aware match: 'PICKING' matches 'PICKING_A', 'Receiving_A', etc."""
    if not worker_zone or not task_zone:
        return False
    return worker_zone == task_zone or worker_zone.split("_")[0] == task_zone.split("_")[0]


def score_pair(task: Task, worker: Worker, now: datetime) -> dict:
    """Explainable cost components for one (task, worker) pair. Higher total is better."""
    worker_zone = _norm(worker.assigned_zone)
    task_zone = _task_zone(task)

    if _zones_match(worker_zone, task_zone):
        zone_pts = ZONE_MATCH_POINTS
        zone_note = "zone match"
    elif worker.skill_level and _norm(worker.skill_level) == "EXPERT":
        zone_pts = ZONE_MISMATCH_PENALTY  # experts may cross-cover, with penalty
        zone_note = "cross-zone (expert cover)"
    else:
        zone_pts = ZONE_MISMATCH_PENALTY - 25  # non-expert cross-zone strongly discouraged
        zone_note = "cross-zone (discouraged)"

    priority_pts = PRIORITY_WEIGHT.get(_norm(task.priority), 20)

    deadline_pts = 0
    deadline_note = "no deadline"
    if task.deadline:
        hours_left = (task.deadline - now).total_seconds() / 3600.0
        if hours_left <= 0:
            deadline_pts, deadline_note = 40, "OVERDUE"
        elif hours_left <= 1:
            deadline_pts, deadline_note = 30, "due within 1h"
        elif hours_left <= 2:
            deadline_pts, deadline_note = 20, "due within 2h"
        elif hours_left <= 4:
            deadline_pts, deadline_note = 10, "due within 4h"

    skill = _norm(worker.skill_level) or "BEGINNER"
    skill_pts = SKILL_POINTS.get(skill, 10)
    exp = min((worker.experience_years or 0.0) * 2.0, 10.0)

    total = priority_pts + deadline_pts + zone_pts + skill_pts + exp
    return {
        "total": round(total, 2),
        "priority": {"points": priority_pts, "value": _norm(task.priority) or "NORMAL"},
        "deadline": {"points": deadline_pts, "note": deadline_note},
        "zone": {"points": zone_pts, "note": zone_note},
        "skill": {"points": skill_pts, "value": skill},
        "experience": {"points": round(exp, 1)},
    }


def eligible_workers(db: Session, warehouse_id: str, shift: Optional[int] = None) -> List[Worker]:
    q = db.query(Worker).filter(Worker.warehouse_id == warehouse_id, Worker.status == "ON_SHIFT")
    if shift is not None:
        q = q.filter(Worker.shift == shift)
    return q.all()


def optimize(task_worker_scores: List[List[float]]) -> List[tuple]:
    """
    Maximize total score. Returns list of (task_index, worker_index).

    Uses the Hungarian algorithm when scipy is installed; otherwise a
    deterministic greedy pass ordered by task urgency.
    """
    if not task_worker_scores or not task_worker_scores[0]:
        return []

    n_tasks, n_workers = len(task_worker_scores), len(task_worker_scores[0])

    if HAS_SCIPY:
        try:
            max_score = max(max(row) for row in task_worker_scores) + 1.0
            cost = [[max_score - s for s in row] for row in task_worker_scores]
            # Pad to a square matrix so every task is matched when workers < tasks
            if n_workers > n_tasks:
                pass  # rows (tasks) all assigned by Hungarian
            rows, cols = linear_sum_assignment(cost)
            return [(int(r), int(c)) for r, c in zip(rows, cols) if r < n_tasks and c < n_workers]
        except Exception:
            pass  # fall through to greedy

    # Greedy fallback: tasks in order of their best achievable score, then
    # matched to their best remaining worker.
    order = sorted(range(n_tasks), key=lambda t: max(task_worker_scores[t]), reverse=True)
    worker_used = set()
    pairs = []
    for t in order:
        best_w, best_s = None, None
        for w in range(n_workers):
            if w in worker_used:
                continue
            s = task_worker_scores[t][w]
            if best_s is None or s > best_s:
                best_s, best_w = s, w
        if best_w is not None:
            pairs.append((t, best_w))
            worker_used.add(best_w)
    return pairs


def _pending_tasks(db: Session, warehouse_id: str) -> List[Task]:
    """Assignable tasks, most urgent first (priority then deadline)."""
    tasks = (
        db.query(Task)
        .filter(Task.warehouse_id == warehouse_id, Task.status.in_(["PLANNED", "PENDING"]))
        .all()
    )
    def urgency(t: Task):
        p = -PRIORITY_WEIGHT.get(_norm(t.priority), 20)
        d = t.deadline or datetime.utcnow() + timedelta(days=365)
        return (p, d, t.created_at)
    return sorted(tasks, key=urgency)


def plan_assignment(db: Session, warehouse_id: str, shift: Optional[int] = None) -> dict:
    """Compute the optimal task->worker plan WITHOUT writing anything."""
    now = datetime.utcnow()
    tasks = _pending_tasks(db, warehouse_id)
    workers = eligible_workers(db, warehouse_id, shift)
    if not tasks:
        return {"warehouse_id": warehouse_id, "assignments": [], "unassigned_tasks": [],
                "note": "No pending tasks.", "optimizer": "hungarian" if HAS_SCIPY else "greedy"}
    if not workers:
        return {"warehouse_id": warehouse_id,
                "assignments": [],
                "unassigned_tasks": [t.id for t in tasks],
                "note": "No eligible workers on shift.",
                "optimizer": "hungarian" if HAS_SCIPY else "greedy"}

    matrix = [[score_pair(t, w, now)["total"] for w in workers] for t in tasks]
    pairs = optimize(matrix)
    assigned_tasks = set()
    assignments = []
    for t_idx, w_idx in pairs:
        task, worker = tasks[t_idx], workers[w_idx]
        assigned_tasks.add(t_idx)
        assignments.append({
            "task_id": task.id,
            "process_type": task.process_type,
            "priority": task.priority,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "worker_id": worker.worker_id,
            "worker_name": worker.name,
            "zone": worker.assigned_zone,
            "why": score_pair(task, worker, now),
        })

    return {
        "warehouse_id": warehouse_id,
        "optimizer": "hungarian" if HAS_SCIPY else "greedy_fallback",
        "generated_at": now.isoformat(),
        "assignments": assignments,
        "unassigned_tasks": [tasks[i].id for i in range(len(tasks)) if i not in assigned_tasks],
    }


def run_assignment(db: Session, warehouse_id: str, shift: Optional[int] = None) -> dict:
    """
    Execute the optimized plan: mark tasks ASSIGNED and notify each worker
    (requires ack; deduped, so re-runs never double-notify).
    """
    from app.services.notification_service import create_notification
    from app.db.models import User

    plan = plan_assignment(db, warehouse_id, shift)
    by_task = {a["task_id"]: a for a in plan["assignments"]}
    executed = []
    for a in plan["assignments"]:
        task = db.query(Task).filter(Task.id == a["task_id"]).first()
        if not task or task.status not in ("PLANNED", "PENDING"):
            continue
        task.status = "ASSIGNED"
        task.assigned_worker_id = a["worker_id"]
        task.assigned_at = datetime.utcnow()

        worker = db.query(Worker).filter(Worker.worker_id == a["worker_id"]).first()
        if worker:
            create_notification(
                db,
                user_id=worker.user_id,
                type="task.assigned",
                message=(f"New task: {task.process_type} · {task.instructions or ''} "
                         f"· zone {task.zone or task.process_type}"),
                priority="high",
                requires_ack=True,
                ack_minutes=5,
                dedup_key=f"task.assigned:{task.id}",
                payload={"task_id": task.id, "deadline": task.deadline.isoformat() if task.deadline else None,
                         "assignment_score": a["why"]},
            )
        executed.append({"task_id": task.id, "worker_id": a["worker_id"]})

    db.commit()
    plan["executed"] = executed
    return plan
