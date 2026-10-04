import json
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from state.models import WarehouseUpdate
from events.models import NetworkEvent
from api.schemas import QueryRequest, QueryResponse, SimulateRequest, SimulateResponse, ApproveDecisionRequest
from state.manager import StateManager
from events.handler import EventHandler
from audit.logger import AuditLogger
from tools.simulation_tools import SimulationTools
from tools.network_tools import NetworkTools
from providers.llm import LLMProvider
from communication.interface import CommunicationAdapter, MessageType
from agent.graph import build_head_office_graph
from agent.nodes import AgentNodes

logger = logging.getLogger(__name__)
router = APIRouter()

# Global dependencies
state_manager = None
event_handler = None
audit_logger = None
simulation_tools = None
llm_provider = None
comm_adapter = None
agent_graph = None
query_graph = None
network_tools = None


def init_routes(sm: StateManager, eh: EventHandler, al: AuditLogger, st: SimulationTools, llm: LLMProvider, ca: CommunicationAdapter, optimizer):
    global state_manager, event_handler, audit_logger, simulation_tools, llm_provider, comm_adapter, agent_graph
    global query_graph, network_tools
    state_manager = sm
    event_handler = eh
    audit_logger = al
    simulation_tools = st
    llm_provider = llm
    comm_adapter = ca

    # Initialize the event-driven LangGraph agent
    from tools.resource_tools import ResourceTools

    nodes = AgentNodes(
        state_manager=sm,
        resource_tools=ResourceTools(sm),
        network_tools=NetworkTools(sm, ca),
        comm_adapter=ca,
        llm=llm,
        optimizer=optimizer
    )
    agent_graph = build_head_office_graph(nodes)
    network_tools = NetworkTools(sm, ca)

    # Initialize the interactive query agent (LLM tool-calling loop)
    chat_model = llm.get_chat_model() if llm else None
    if chat_model is not None:
        from agent.tools import build_head_office_tools
        from agent.query_graph import build_query_graph
        ho_tools = build_head_office_tools(sm, al)
        query_graph, _ = build_query_graph(chat_model, ho_tools)
        logger.info("Query agent initialized with tools")
    else:
        query_graph = None
        logger.warning("No LLM chat model available; /query falls back to deterministic answers")


def _grounded_fallback_answer(query: str) -> str:
    """Deterministic, data-grounded answer when no LLM is configured."""
    network = network_tools.get_network_state()
    warehouses = network.get("warehouses", {})
    if not warehouses:
        return ("No warehouses have reported state yet. Send updates to "
                "/warehouse-update or wait for the backend sync (every 60s).")

    shortages = [
        f"{wh_id} (short {s['workers_required'] - s['workers']})"
        for wh_id, s in warehouses.items()
        if s.get("workers", 0) < s.get("workers_required", 0)
    ]
    high_risk = [wh_id for wh_id, s in warehouses.items() if s.get("risk_score", 0) > 0.7]
    busiest = max(warehouses.items(), key=lambda kv: kv[1].get("capacity_utilization", 0))

    lines = [
        f"[Deterministic mode - no LLM key] Network snapshot across {len(warehouses)} warehouse(s):",
        f"- Highest utilization: {busiest[0]} at {busiest[1].get('capacity_utilization', 0):.0%}",
    ]
    if shortages:
        lines.append(f"- Worker shortages: {', '.join(shortages)}")
    if high_risk:
        lines.append(f"- High risk (>0.7): {', '.join(high_risk)}")
    if not shortages and not high_risk:
        lines.append("- No active shortages or high-risk warehouses detected.")
    return "\n".join(lines)


@router.post("/events")
async def handle_event(event: NetworkEvent):
    # Setup initial state for the graph
    initial_state = {
        "request_id": event.event_id,
        "current_event": event.model_dump(mode="json"),
        "messages": [],
        "affected_warehouses": [],
        "observations": [],
        "tool_calls": [],
        "tool_results": [],
        "identified_problems": [],
        "resource_shortages": [],
        "resource_surpluses": [],
        "candidate_actions": [],
        "selected_action": None,
        "recommendation": None,
        "validation_result": None,
        "approval_status": None,
        "execution_result": None,
        "final_response": None,
        "errors": [],
        "timestamps": {}
    }

    # Run the graph
    config = {"configurable": {"thread_id": event.event_id}}
    async for output in agent_graph.astream(initial_state, config=config):
        pass  # Stream processing can be handled here if needed

    # Get final state
    state = agent_graph.get_state(config)

    # Log decision if generated (decision_id lets the UI approve it later)
    if state.values.get("recommendation"):
        rec = state.values["recommendation"]
        audit_logger.log_decision(
            decision_id=event.event_id,
            event=event.type.value,
            warehouse=event.warehouse_id,
            tools_called=[call["tool"] for call in state.values.get("tool_results", [])],
            recommendation=(f"Allocate {rec.get('quantity', '?')} workers "
                            f"from {rec.get('source_warehouse', '?')} "
                            f"to {rec.get('target_warehouse', '?')}"
                            if rec.get("type") == "WORKER_ALLOCATION"
                            else str(rec.get("type", "RECOMMENDATION"))),
            reasoning=rec.get("reason", []),
            status=state.values.get("approval_status")
        )

    return {
        "event_id": event.event_id,
        "status": state.values.get("approval_status", "PROCESSED"),
        "recommendation": state.values.get("recommendation"),
        "response": state.values.get("final_response")
    }


@router.post("/warehouse-update")
def warehouse_update(update: WarehouseUpdate):
    state_manager.process_warehouse_update(update)
    return {"status": "success"}


@router.get("/network-state")
def get_network_state():
    """Live network snapshot plus derived stats the dashboard renders."""
    state = state_manager.get_network_state().model_dump()
    warehouses = state.get("warehouses", {})
    pending = len(audit_logger.get_pending_decisions()) if audit_logger else 0

    if warehouses:
        avg_risk = sum(w.get("risk_score", 0) for w in warehouses.values()) / len(warehouses)
        shortages = sum(1 for w in warehouses.values() if w.get("workers", 0) < w.get("workers_required", 0))
        overall_health = "CRITICAL" if avg_risk > 0.7 else ("ATTENTION" if avg_risk > 0.4 or shortages else "GOOD")
        active_alerts = len(network_tools.get_active_events()) if network_tools else 0
    else:
        avg_risk = 0.0
        overall_health = "NO_DATA"
        active_alerts = 0
        shortages = 0

    return {
        "warehouses": warehouses,
        "total_warehouses": len(warehouses),
        "overall_health": overall_health,
        "average_risk": round(avg_risk, 3),
        "worker_shortages": shortages,
        "active_alerts": active_alerts,
        "pending_decisions": pending,
    }


@router.get("/events/active")
def get_active_events():
    """Currently active network issues (worker shortages, capacity warnings)."""
    if network_tools is None:
        return []
    return network_tools.get_active_events()


@router.post("/query", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    # Interactive agent: LLM tool-calling loop over live network state
    if query_graph is not None:
        try:
            from agent.query_graph import run_query
            answer, tools_used = run_query(query_graph, request.query)
            return QueryResponse(response=answer, tools_used=tools_used)
        except Exception:
            logger.exception("Query agent failed; using deterministic fallback")

    return QueryResponse(response=_grounded_fallback_answer(request.query), tools_used=["network_state_snapshot"])


@router.post("/simulate")
def simulate(request: SimulateRequest):
    result = simulation_tools.simulate_action(request.scenario)
    return result


@router.post("/approve")
async def approve_decision(request: ApproveDecisionRequest):
    new_status = "APPROVED" if request.approved else "REJECTED"

    # 1. Decisions created from interactive chat have an audit entry only
    entry = audit_logger.resolve_decision(request.decision_id, new_status) if audit_logger else None

    # 2. Event-driven decisions may have an interrupted graph thread to resume
    executed = None
    try:
        config = {"configurable": {"thread_id": request.decision_id}}
        state = agent_graph.get_state(config)
        if state and state.next:
            # Check if already processed
            current_status = state.values.get("approval_status")
            if current_status in ("APPROVED", "REJECTED"):
                return {"decision_id": request.decision_id, "status": current_status, 
                        "execution_result": state.values.get("execution_result"),
                        "message": "Decision already processed"}
            agent_graph.update_state(config, {"approval_status": new_status}, as_node="HumanApproval")
            async for output in agent_graph.astream(None, config=config):
                pass
            final_state = agent_graph.get_state(config)
            executed = final_state.values.get("execution_result")
    except Exception:
        logger.exception("No resumable graph thread for decision %s", request.decision_id)

    if entry is None and executed is None:
        raise HTTPException(status_code=404, detail="Decision not found or not pending approval.")

    return {
        "decision_id": request.decision_id,
        "status": new_status,
        "execution_result": executed,
        "final_response": (executed or {}).get("message") if isinstance(executed, dict) else None
    }


@router.get("/decisions")
def get_decisions():
    return audit_logger.get_logs()


@router.get("/decisions/pending")
def get_pending_decisions():
    return audit_logger.get_pending_decisions()


@router.get("/health")
def health():
    return {"status": "healthy", "llm_enabled": query_graph is not None}


from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BookingItem(BaseModel):
    product_id: int
    expected_quantity: int

class BookingRequest(BaseModel):
    supplier: str
    expected_arrival: str
    priority: str
    items: List[BookingItem]

BACKEND_URL = os.environ.get("WAREHOUSE_BACKEND_URL", "http://backend:8000")
BACKEND_USER = os.environ.get("WAREHOUSE_BACKEND_USER", "manager")
BACKEND_PASSWORD = os.environ.get("WAREHOUSE_BACKEND_PASSWORD", "password")

@router.post("/bookings")
async def create_booking(request: BookingRequest):
    # Determine the best warehouse to send this to.
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            # 1. Login to get token
            auth_resp = await client.post(
                f"{BACKEND_URL}/api/auth/login",
                data={"username": BACKEND_USER, "password": BACKEND_PASSWORD},
            )
            if auth_resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to authenticate with warehouse backend")
            token = auth_resp.json().get("access_token")

            # 2. Send booking with token
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.post(
                f"{BACKEND_URL}/api/inbound/shipments",
                json=request.model_dump(mode="json"), headers=headers,
            )

            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            return {
                "status": "success",
                "assigned_warehouse": "WH-001",
                "warehouse_response": resp.json()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Booking failed")
            raise HTTPException(status_code=502, detail=str(e))
