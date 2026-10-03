"""
Planning & Validation Pipeline (Phase 4) -- explicit state machine.

Steps (each with clear inputs/outputs and failure handling):
  1. VALIDATE_DATA       instruction shape, items present, quantities sane
  2. CHECK_INVENTORY     available stock vs required (WARN on shortfall)
  3. CHECK_CAPACITY      storage capacity for inbound-style ops (WARN on tight)
  4. FORECAST_WORKLOAD   expected workload for the operation (units -> hours)
  5. CALCULATE_MANPOWER  labor standards -> required headcount
  6. OPTIMIZE_RESOURCES  propose task split per process/zone
  7. GENERATE_TASKS      persist tasks with zone + SLA deadline
  8. VALIDATE_PLAN       plan sanity (task coverage vs items)
  9. ASSIGN_TASKS        preview of optimal assignment (Execution is human-approved)

Every step is logged on a PlanRun row so Planned vs Actual and debugging
have a full audit trail from day one.
"""
import logging
import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..connection_center.canonical_models import HeadOfficeInstruction
from ..db.models import (
    InventoryRecord, Task, OutboundOrder, OutboundOrderItem, OperationalEvent,
    StorageLocation, LaborStandard, PlanRun, Product,
)
from ..intelligence.workforce import headcount_needed
from ..intelligence.assignment import plan_assignment

logger = logging.getLogger(__name__)

OPERATION_TO_PROCESSES = {
    "PICK_PACK_SHIP": ["PICKING", "PACKING"],
    "REPLENISH": ["PUTAWAY"],
    "CROSS_DOCK": ["DISPATCH"],
}
DEFAULT_UPH = 50.0


class PipelineStepError(Exception):
    def __init__(self, step: str, detail: str):
        self.step = step
        super().__init__(f"[{step}] {detail}")


class PlanningPipeline:
    """State-machine pipeline: instruction -> validated task plan."""

    STEPS = [
        "VALIDATE_DATA", "CHECK_INVENTORY", "CHECK_CAPACITY", "FORECAST_WORKLOAD",
        "CALCULATE_MANPOWER", "OPTIMIZE_RESOURCES", "GENERATE_TASKS",
        "VALIDATE_PLAN", "ASSIGN_TASKS",
    ]

    def __init__(self, db: Session):
        self.db = db
        self.plan = None
        self.trace = []
        self.context = {}

    # ---------- state machine plumbing ----------
    @staticmethod
    def _json_safe(value):
        return json.loads(json.dumps(value, default=str))

    def _step(self, name: str, fn):
        """Run one step; record OK / WARN / FAILED with detail."""
        entry = {"step": name, "status": "OK", "detail": None, "at": datetime.utcnow().isoformat()}
        try:
            detail = fn()
            if isinstance(detail, tuple):  # (status, detail) for WARN
                entry["status"], entry["detail"] = detail
            else:
                entry["detail"] = detail
        except PipelineStepError as e:
            entry["status"], entry["detail"] = "FAILED", str(e)
            self.trace.append(entry)
            self._persist("FAILED")
            raise
        entry["detail"] = self._json_safe(entry["detail"])
        self.trace.append(entry)
        self._persist("RUNNING")
        return self.context.get(f"out_{name}")

    def _persist(self, status: str):
        self.plan.steps = list(self.trace)
        self.plan.status = status
        self.db.add(self.plan)
        self.db.commit()

    # ---------- public API ----------
    def execute(self, instruction: HeadOfficeInstruction):
        self.plan = PlanRun(
            plan_id=f"plan_{uuid.uuid4().hex[:10]}",
            instruction_id=instruction.instruction_id,
            warehouse_id=instruction.fulfillment_center,
        )
        self.db.add(self.plan)
        self.db.commit()
        logger.info(f"Planning pipeline {self.plan.plan_id} starting for instruction {instruction.instruction_id}")

        try:
            self._step("VALIDATE_DATA", lambda: self._validate(instruction))
            self._step("CHECK_INVENTORY", lambda: self._check_inventory(instruction))
            self._step("CHECK_CAPACITY", lambda: self._check_capacity(instruction))
            self._step("FORECAST_WORKLOAD", lambda: self._forecast_workload(instruction))
            self._step("CALCULATE_MANPOWER", lambda: self._calculate_manpower(instruction))
            self._step("OPTIMIZE_RESOURCES", lambda: self._optimize_resources(instruction))
            self._step("GENERATE_TASKS", lambda: self._generate_tasks(instruction))
            self._step("VALIDATE_PLAN", lambda: self._validate_plan(instruction))
            self._step("ASSIGN_TASKS", lambda: self._assign_tasks(instruction))
        except PipelineStepError as e:
            logger.error(f"Pipeline {self.plan.plan_id} failed: {e}")
            raise

        self._persist("COMPLETED")
        return {
            "status": "success",
            "plan_id": self.plan.plan_id,
            "tasks_created": len(self.context.get("out_GENERATE_TASKS", [])),
            "manpower": self.context.get("out_CALCULATE_MANPOWER"),
            "proposed_assignments": self.context.get("out_ASSIGN_TASKS", {}).get("assignments", []),
            "trace": self.trace,
        }

    # ---------- steps ----------
    def _validate(self, instruction: HeadOfficeInstruction):
        if not instruction.items:
            raise PipelineStepError("VALIDATE_DATA", "Instruction contains no items.")
        bad = [i for i in instruction.items if i.quantity <= 0]
        if bad:
            raise PipelineStepError("VALIDATE_DATA", f"{len(bad)} item(s) with non-positive quantity.")
        if instruction.sla_hours <= 0:
            raise PipelineStepError("VALIDATE_DATA", "SLA must be positive hours.")
        return {"items": len(instruction.items), "total_units": sum(i.quantity for i in instruction.items)}

    def _check_inventory(self, instruction: HeadOfficeInstruction):
        shortfalls = []
        if instruction.required_operation in ["PICK_PACK_SHIP", "CROSS_DOCK"]:
            for item in instruction.items:
                product = self.db.query(Product).filter(Product.sku == item.sku_id).first()
                if not product:
                    shortfalls.append({"sku": item.sku_id, "reason": "unknown SKU"})
                    continue
                inv = (
                    self.db.query(InventoryRecord)
                    .filter(
                        InventoryRecord.warehouse_id == instruction.fulfillment_center,
                        InventoryRecord.product_id == product.id,
                    )
                    .first()
                )
                available = (inv.quantity - inv.reserved_quantity) if inv else 0
                if available < item.quantity:
                    shortfalls.append({"sku": item.sku_id, "needed": item.quantity, "available": available})
                elif inv:
                    inv.reserved_quantity += item.quantity  # soft reservation
        self.context["inventory_shortfalls"] = shortfalls
        self.db.commit()
        if shortfalls:
            return ("WARN", f"{len(shortfalls)} item(s) short on stock; proceeding as backorder.")
        return "sufficient inventory; reserved quantities updated"

    def _check_capacity(self, instruction: HeadOfficeInstruction):
        if instruction.required_operation == "REPLENISH":
            total = sum(i.quantity for i in instruction.items)
            locations = self.db.query(StorageLocation).filter(
                StorageLocation.warehouse_id == instruction.fulfillment_center,
                StorageLocation.is_available == True,  # noqa: E712
            ).all()
            free = sum(l.capacity - l.current_occupancy for l in locations)
            self.context["free_capacity"] = free
            if free < total:
                return ("WARN", f"Free capacity {free} < required {total}.")
            return f"free capacity {free} units"
        return "capacity check not applicable to this operation"

    def _forecast_workload(self, instruction: HeadOfficeInstruction):
        """Units -> per-process hours using labor standards; also feeds historical record."""
        processes = OPERATION_TO_PROCESSES.get(instruction.required_operation, ["PICKING"])
        total_units = sum(i.quantity for i in instruction.items)
        forecast = {}
        for proc in processes:
            std = self.db.query(LaborStandard).filter(
                LaborStandard.warehouse_id == instruction.fulfillment_center,
                LaborStandard.process_type == proc,
            ).first()
            uph = std.units_per_hour if std else DEFAULT_UPH
            forecast[proc] = {"units": total_units, "hours": round(total_units / uph, 2), "units_per_hour": uph}
        self.context["out_FORECAST_WORKLOAD"] = forecast
        return forecast

    def _calculate_manpower(self, instruction: HeadOfficeInstruction):
        processes = self.context["out_FORECAST_WORKLOAD"]
        manpower = {}
        for proc, f in processes.items():
            std = self.db.query(LaborStandard).filter(
                LaborStandard.warehouse_id == instruction.fulfillment_center,
                LaborStandard.process_type == proc,
            ).first()
            if std:
                manpower[proc] = headcount_needed(f["units"], std)
            else:
                manpower[proc] = max(1, int(f["hours"] / 7.0) + 1)
        self.context["out_CALCULATE_MANPOWER"] = manpower
        return manpower

    def _optimize_resources(self, instruction: HeadOfficeInstruction):
        """Split the instruction into executable tasks (one per process)."""
        processes = OPERATION_TO_PROCESSES.get(instruction.required_operation, ["PICKING"])
        deadline = datetime.utcnow() + timedelta(hours=instruction.sla_hours)
        plan = [{
            "process_type": p,
            "zone": p,
            "priority": instruction.priority,
            "deadline": deadline,
        } for p in processes]
        self.context["out_OPTIMIZE_RESOURCES"] = plan
        return plan

    def _generate_tasks(self, instruction: HeadOfficeInstruction):
        plan = self.context["out_OPTIMIZE_RESOURCES"]
        wh = instruction.fulfillment_center

        # In PICK_PACK_SHIP, persist the outbound order too
        if instruction.required_operation == "PICK_PACK_SHIP":
            existing = self.db.query(OutboundOrder).filter(
                OutboundOrder.order_id == f"ORD-{instruction.order_id}"
            ).first()
            if not existing:
                order = OutboundOrder(
                    order_id=f"ORD-{instruction.order_id}",
                    warehouse_id=wh,
                    customer=instruction.fulfillment_center,
                    status="CREATED",
                    priority=instruction.priority,
                    required_dispatch_time=datetime.utcnow() + timedelta(hours=instruction.sla_hours),
                    total_items=sum(i.quantity for i in instruction.items),
                )
                self.db.add(order)

        task_ids = []
        for t in plan:
            task = Task(
                warehouse_id=wh,
                process_type=t["process_type"],
                zone=t["zone"],
                priority=t["priority"],
                status="PLANNED",
                deadline=t["deadline"],
                instructions=(f"Instruction {instruction.instruction_id}: "
                              f"{instruction.required_operation}, "
                              f"{sum(i.quantity for i in instruction.items)} units"),
                reference_id=instruction.instruction_id,
            )
            self.db.add(task)
            self.db.flush()
            task_ids.append(task.id)

        self.db.add(OperationalEvent(
            warehouse_id=wh,
            event_type="PLAN_GENERATED",
            description=f"Plan {self.plan.plan_id}: {len(task_ids)} task(s) from instruction {instruction.instruction_id}",
            details={"plan_id": self.plan.plan_id, "task_ids": task_ids},
            reference_id=instruction.instruction_id,
        ))
        self.db.commit()
        self.context["out_GENERATE_TASKS"] = task_ids
        return task_ids

    def _validate_plan(self, instruction: HeadOfficeInstruction):
        task_ids = self.context.get("out_GENERATE_TASKS", [])
        expected = len(OPERATION_TO_PROCESSES.get(instruction.required_operation, ["PICKING"]))
        if len(task_ids) != expected:
            raise PipelineStepError("VALIDATE_PLAN", f"Plan produced {len(task_ids)} task(s), expected {expected}.")
        return f"{len(task_ids)} task(s) cover the instruction"

    def _assign_tasks(self, instruction: HeadOfficeInstruction):
        """Preview the assignment. Committing it is a manager action (human-in-the-loop)."""
        preview = plan_assignment(self.db, instruction.fulfillment_center)
        self.context["out_ASSIGN_TASKS"] = preview
        n = len(preview.get("assignments", []))
        return f"{n} task -> worker assignment(s) proposed (awaiting manager approval to execute)"
