from fastapi import APIRouter, HTTPException, Depends
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
from api.auth import get_current_user
from services.nvidia_service import NvidiaService

router = APIRouter()
nvidia_service = NvidiaService()

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
async def handle_event(event: NetworkEvent, current_user: str = Depends(get_current_user)):
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
    
    config = {"configurable": {"thread_id": event.event_id}}
    async for output in agent_graph.astream(initial_state, config=config):
        pass
    
    state = agent_graph.get_state(config)
    
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
def warehouse_update(update: WarehouseUpdate, current_user: str = Depends(get_current_user)):
    state_manager.process_warehouse_update(update)
    return {"status": "success"}

@router.get("/network-state")
def get_network_state(current_user: str = Depends(get_current_user)):
    return state_manager.get_network_state()

@router.post("/query")
def query_agent(request: QueryRequest, current_user: str = Depends(get_current_user)):
    # Get current warehouse context
    warehouse_state = state_manager.get_network_state()
    
    # Send to NvidiaService for reasoning
    response = nvidia_service.generate_reasoning(warehouse_state, request.query)
    
    # If it failed and returned a string, wrap it. Else it is a dict with answer, severity, etc.
    return {
        "response": response.get("answer", ""),
        "severity": response.get("severity", "unknown"),
        "recommendations": response.get("recommendations", []),
        "reasoning": response.get("reasoning", ""),
        "tools_used": ["nvidia_service"]
    }

@router.post("/simulate")
def simulate(request: SimulateRequest, current_user: str = Depends(get_current_user)):
    result = simulation_tools.simulate_action(request.scenario)
    return result

@router.post("/approve")
async def approve_decision(request: ApproveDecisionRequest, current_user: str = Depends(get_current_user)):
    config = {"configurable": {"thread_id": request.decision_id}}
    
    state = agent_graph.get_state(config)
    if not state or not state.next:
        raise HTTPException(status_code=404, detail="Decision not found or not pending approval.")
        
    new_status = "APPROVED" if request.approved else "REJECTED"
    agent_graph.update_state(config, {"approval_status": new_status})
    
    async for output in agent_graph.astream(None, config=config):
        pass
        
    final_state = agent_graph.get_state(config)
    return {
        "status": new_status,
        "execution_result": final_state.values.get("execution_result"),
        "final_response": final_state.values.get("final_response")
    }

@router.get("/decisions")
def get_decisions(current_user: str = Depends(get_current_user)):
    return audit_logger.get_logs()

@router.get("/dashboard/metrics")
def get_dashboard_metrics(current_user: str = Depends(get_current_user)):
    # Mock real calculation based on state manager
    # In a real app this would query the DB or network state properly
    return {
        "ordersToday": 320,
        "pendingOrders": 55,
        "inboundShipments": 18,
        "outboundShipments": 22,
        "presentWorkers": 45,
        "requiredWorkers": 50,
        "utilizationPercent": 92,
        "delayedTasks": 3
    }

@router.get("/health")
def health():
    return {
        "warehouse_agent": "online",
        "database": "connected",
        "ml_models": "ready",
        "nvidia_api": nvidia_service.check_health()
    }

from pydantic import BaseModel
class OrderWebhookPayload(BaseModel):
    order_id: str
    product: dict
    customer: dict
    timestamp: str

@router.post("/orders/webhook")
def receive_store_order(order: OrderWebhookPayload):
    # Process the incoming order through the Head Agent Orchestrator
    
    # 1. Create Order in Central State
    new_order = state_manager.create_order(
        order_id=order.order_id, 
        customer=order.customer, 
        items=[order.product]
    )
    
    # 2. Check Inventory and Allocate FC
    allocated_wh = state_manager.check_inventory_and_allocate(order.order_id)
    
    # 3. Log the decision
    if audit_logger:
        audit_logger.log_decision(
            event="NEW_STOREFRONT_ORDER",
            warehouse=allocated_wh if allocated_wh else "SELLER_DIRECT",
            tools_called=["check_inventory_and_allocate"],
            recommendation=f"Route order {order.order_id} to {allocated_wh if allocated_wh else 'Seller'}",
            reasoning=[f"Customer location: {order.customer.get('city')}", f"Allocation: {allocated_wh}"],
            status="ALLOCATED" if allocated_wh else "ESCALATED"
        )
        
    return {
        "status": "success",
        "message": f"Order {order.order_id} processed by Head Office Agent.",
        "allocated_warehouse": allocated_wh if allocated_wh else "SELLER_DIRECT_INBOUND"
    }
