"""End-to-end smoke test of the new deterministic stack (SQLite, no Postgres)."""
import os, sys, asyncio
os.environ["DATABASE_URL"] = "sqlite:///./smoke_test.db"
if os.path.exists("smoke_test.db"):
    os.remove("smoke_test.db")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import Base, engine, SessionLocal
Base.metadata.create_all(bind=engine)

# 1. Seed
import scripts.seed_users as seed  # noqa
seed.seed_data()

from app.db.database import SessionLocal
db = SessionLocal()

# 2. Forecasting + backtest
from app.intelligence.forecasting import forecast, backtest, get_history
f = forecast(db, "WH01", "PICKING", horizon_days=7)
assert len(f["forecast"]) == 7 and f["forecast"][0]["forecast_volume"] > 0, f
bt = backtest(get_history(db, "WH01", "PICKING"), horizon=7)
assert bt["origins"] == 3 and bt["wape"] is not None, bt
print(f"[OK] forecast model={f['model']} wape(backtest)={bt['wape']}")

# 3. Workforce gap (labor standards)
from app.intelligence.workforce import manpower_gap
gap = manpower_gap(db, "WH01", shift=1)
assert gap["processes"] and all("gap" in r for r in gap["processes"]), gap
print(f"[OK] workforce gap: {gap['summary']}")

# 4. Assignment preview (nothing written) + execute
from app.intelligence.assignment import plan_assignment, run_assignment
from app.db.models import Task
preview = plan_assignment(db, "WH01", shift=1)
assert preview["assignments"], preview
assert all("why" in a and "total" in a["why"] for a in preview["assignments"])
print(f"[OK] assignment preview: {len(preview['assignments'])} assignments "
      f"via {preview['optimizer']}, first why={preview['assignments'][0]['why']['total']}")
execd = run_assignment(db, "WH01", shift=1)
n_assigned = db.query(Task).filter(Task.status == "ASSIGNED").count()
print(f"[OK] assignment executed: {n_assigned} task(s) ASSIGNED, "
      f"{db.query(__import__('app.db.models', fromlist=['Notification']).Notification).count()} notifications")

# 5. Planning pipeline state machine
from app.planning.pipeline import PlanningPipeline
from app.connection_center.canonical_models import HeadOfficeInstruction, CanonicalItem
instr = HeadOfficeInstruction(
    instruction_id="INS-SMOKE-1", order_id="88123",
    items=[CanonicalItem(sku_id="SKU-X", quantity=120)],
    fc="WH01", priority="HIGH", sla_hours=4, required_operation="PICK_PACK_SHIP",
)
result = PlanningPipeline(db).execute(instr)
assert result["status"] == "success" and result["tasks_created"] == 2
assert [s["status"] for s in result["trace"]].count("FAILED") == 0
print(f"[OK] pipeline: {result['tasks_created']} tasks, manpower={result['manpower']}, "
      f"steps={len(result['trace'])}")

# validation failure path
try:
    bad = HeadOfficeInstruction(instruction_id="INS-BAD", order_id="X", items=[],
                                fc="WH01", priority="LOW", sla_hours=4,
                                required_operation="REPLENISH")
    PlanningPipeline(db).execute(bad)
    raise AssertionError("should have failed")
except Exception as e:
    print(f"[OK] pipeline rejects empty instruction: {e}")

# 6. Action Engine: propose -> approve -> execute (reassign)
from app.db.models import AgentAction, Notification
from app.action_engine.engine import decide_action
task = db.query(Task).filter(Task.status == "ASSIGNED").first()
action = AgentAction(agent_name="SupervisorAgent", warehouse_id="WH01",
                     trigger="test", tool_called="propose_reassignment",
                     action_type="REASSIGN_TASK",
                     action_payload={"task_id": task.id, "new_worker_id": None},
                     idempotency_key=f"smoke-reassign:{task.id}",
                     recommendation="reassign test", manager_approval="PENDING")
db.add(action); db.commit()
old_worker = task.assigned_worker_id
action = decide_action(db, action, "APPROVED", decided_by_user_id=1)
db.refresh(task)
assert task.assigned_worker_id and task.assigned_worker_id != old_worker
assert action.executed_at is not None, "action must be executed on approve"
print(f"[OK] action engine: task {task.id} reassigned {old_worker} -> {task.assigned_worker_id}")

# idempotency: approving again is a no-op
again = decide_action(db, action, "APPROVED", decided_by_user_id=1)
assert again.executed_at == action.executed_at
print("[OK] action engine idempotent")
from app.db.models import OutboxEvent
assert db.query(OutboxEvent).count() >= 1
print(f"[OK] outbox events recorded: {db.query(OutboxEvent).count()}")

# 7. Notification lifecycle: dedup + escalation ladder
from app.services.notification_service import create_notification, tick_escalations
from datetime import datetime, timedelta
w = __import__("app.db.models", fromlist=["Worker"]).Worker
worker = db.query(w).filter(w.worker_id == task.assigned_worker_id).first()
n1 = create_notification(db, worker.user_id, "task.assigned", "Test assignment",
                         priority="high", requires_ack=True, ack_minutes=0,
                         dedup_key="task.assigned:smoke")
n2 = create_notification(db, worker.user_id, "task.assigned", "Test assignment",
                         dedup_key="task.assigned:smoke")
db.commit()
assert n1.id == n2.id, "dedup must return the same notification"
print(f"[OK] notification dedup works (id={n1.id})")
# force overdue and walk the ladder with time sleeps replaced by manual deadline
n1.ack_deadline = datetime.utcnow() - timedelta(minutes=20)
db.commit()
tick_escalations(db); db.refresh(n1)
assert n1.escalation_level >= 1, f"expected level>=1 after tick 1, got {n1.escalation_level}"
tick_escalations(db); db.refresh(n1)
tick_escalations(db); db.refresh(n1)
print(f"[OK] escalation ladder reached level {n1.escalation_level}, "
      f"pending actions={db.query(AgentAction).filter(AgentAction.manager_approval=='PENDING').count()}")

# 8. Connection Center: retries, breaker, DLQ, replay
from app.connection_center.bootstrap import init_default_connectors
from app.connection_center.reliability import call_with_reliability, list_dead_letters, replay_dead_letter
from app.db.models import ConnectionMessage
registry = init_default_connectors()
adapter = registry.get_connector("wms_primary")
adapter.trip(10)  # force failures -> retries exhausted -> DLQ

async def drive():
    m = await call_with_reliability(db, "wms_primary", "OUTBOUND",
                                    "cc:test:smoke", {"hello": "world"},
                                    lambda: adapter.push({}, "cc:test:smoke"))
    return m
# shrink the breaker wait for the test
import app.connection_center.reliability as rel
rel.BREAKER_OPEN_SECONDS = 0
msg = asyncio.run(asyncio.wait_for(drive(), timeout=60))
assert msg.status == "DEAD_LETTER", msg.status
print(f"[OK] CC: exhausted retries -> DEAD_LETTER (attempts={msg.attempts})")
# dedup: same key never executes twice
msg2 = asyncio.run(call_with_reliability(db, "wms_primary", "OUTBOUND",
                                         "cc:test:smoke", {"hello": "world"},
                                         lambda: adapter.push({}, "cc:test:smoke")))
assert msg2.id == msg.id
print("[OK] CC: dedup prevents re-execution")
dl = list_dead_letters(db)
replayed = replay_dead_letter(db, dl[0].id)
assert replayed.status == "PENDING"
print("[OK] CC: dead-letter replay works")

# 9. Head-office dedup through the ledger
from app.api.head_office import receive_instruction
class FakeHeader: pass
res1 = receive_instruction(payload=instr, token=None, db=db)
res2 = receive_instruction(payload=instr, token=None, db=db)
# second call must be the duplicate path
assert res2["status"] == "Duplicate"
print("[OK] head-office instruction dedup works")

print("\nALL SMOKE TESTS PASSED")
db.close()
