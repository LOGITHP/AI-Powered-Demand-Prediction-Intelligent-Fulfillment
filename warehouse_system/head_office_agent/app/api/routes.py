from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from state.models import WarehouseUpdate
from events.models import NetworkEvent
from api.schemas import QueryRequest, QueryResponse, SimulateRequest, SimulateResponse, ApproveDecisionRequest
from state.manager import StateManager
from events.handler import EventHandler
from audit.logger import AuditLogger
from tools.simulation_tools import SimulationTools
from providers.llm import LLMProvider
from communication.interface import CommunicationAdapter, MessageType
from agent.graph import build_head_office_graph
from agent.nodes import AgentNodes

router = APIRouter()

# Global dependencies
state_manager = None 
event_handler = None
audit_logger = None
simulation_tools = None
llm_provider = None
comm_adapter = None
agent_graph = None

def init_routes(sm: StateManager, eh: EventHandler, al: AuditLogger, st: SimulationTools, llm: LLMProvider, ca: CommunicationAdapter, optimizer):
    global state_manager, event_handler, audit_logger, simulation_tools, llm_provider, comm_adapter, agent_graph
    state_manager = sm
    event_handler = eh
    audit_logger = al
    simulation_tools = st
    llm_provider = llm
    comm_adapter = ca
    
    # Initialize the LangGraph agent
    from tools.resource_tools import ResourceTools
    from tools.network_tools import NetworkTools
    
    nodes = AgentNodes(
        state_manager=sm,
        resource_tools=ResourceTools(sm),
        network_tools=NetworkTools(sm, ca),
        comm_adapter=ca,
        llm=llm,
        optimizer=optimizer
    )
    agent_graph = build_head_office_graph(nodes)

@router.post("/events")
async def handle_event(event: NetworkEvent):
    # Setup initial state for the graph
    initial_state = {
        "request_id": event.event_id,
        "current_event": event.model_dump(),
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
        pass # Stream processing can be handled here if needed
    
    # Get final state
    state = agent_graph.get_state(config)
    
    # Log decision if generated
    if state.values.get("recommendation"):
        rec = state.values["recommendation"]
        audit_logger.log_decision(
            event=event.type.value,
            warehouse=event.warehouse_id,
            tools_called=[call["tool"] for call in state.values.get("tool_results", [])],
            recommendation=f"Allocate {rec.get('quantity')} workers from {rec.get('source_warehouse')}",
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
    return state_manager.get_network_state()

@router.post("/query", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    # We would initialize graph with the query here
    response = llm_provider.generate_response(request.query)
    return QueryResponse(response=response, tools_used=[])

@router.post("/simulate")
def simulate(request: SimulateRequest):
    result = simulation_tools.simulate_action(request.scenario)
    return result

@router.post("/approve")
async def approve_decision(request: ApproveDecisionRequest):
    # Resume the interrupted graph execution
    config = {"configurable": {"thread_id": request.decision_id}}
    
    state = agent_graph.get_state(config)
    if not state or not state.next:
        raise HTTPException(status_code=404, detail="Decision not found or not pending approval.")
        
    # Update the state with the approval status
    new_status = "APPROVED" if request.approved else "REJECTED"
    agent_graph.update_state(config, {"approval_status": new_status})
    
    # Continue graph execution
    async for output in agent_graph.astream(None, config=config):
        pass
        
    final_state = agent_graph.get_state(config)
    return {
        "status": new_status,
        "execution_result": final_state.values.get("execution_result"),
        "final_response": final_state.values.get("final_response")
    }

@router.get("/decisions")
def get_decisions():
    return audit_logger.get_logs()

@router.get("/health")
def health():
    return {"status": "healthy"}

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import httpx

class BookingItem(BaseModel):
    product_id: int
    expected_quantity: int

class BookingRequest(BaseModel):
    supplier: str
    expected_arrival: str
    priority: str
    items: List[BookingItem]

@router.post("/bookings")
async def create_booking(request: BookingRequest):
    # Determine the best warehouse to send this to.
    # In a real setup, we'd use state_manager or LangGraph.
    # We will pick "WH-001" (our local warehouse) which runs on backend:8000
    target_warehouse_url = "http://backend:8000/api/inbound/shipments"
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(target_warehouse_url, json=request.dict())
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
            # Update our state manager loosely
            state_manager.network_state.pending_decisions += 1
            
            return {
                "status": "success", 
                "assigned_warehouse": "WH-001",
                "warehouse_response": resp.json()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

