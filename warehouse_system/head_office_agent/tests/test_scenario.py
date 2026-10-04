import pytest
import asyncio
from datetime import datetime
from state.repository import InMemoryNetworkStateRepository
from state.manager import StateManager
from state.models import WarehouseUpdate, OperationalState, Predictions, Alert
from communication.mock_adapter import MockCommunicationAdapter
from tools.resource_tools import ResourceTools
from tools.network_tools import NetworkTools
from providers.llm import MockLLMProvider
from providers.optimization import RealOptimizationProvider
from agent.nodes import AgentNodes
from agent.graph import build_head_office_graph

@pytest.fixture
def setup_agent():
    repo = InMemoryNetworkStateRepository()
    state_manager = StateManager(repo)
    comm_adapter = MockCommunicationAdapter()
    resource_tools = ResourceTools(state_manager)
    network_tools = NetworkTools(state_manager, comm_adapter)
    llm = MockLLMProvider()
    optimizer = RealOptimizationProvider()
    
    nodes = AgentNodes(
        state_manager=state_manager,
        resource_tools=resource_tools,
        network_tools=network_tools,
        comm_adapter=comm_adapter,
        llm=llm,
        optimizer=optimizer
    )
    
    agent_graph = build_head_office_graph(nodes)
    
    # Setup initial state
    wh_a_update = WarehouseUpdate(
        warehouse_id="WH-A",
        timestamp=datetime.utcnow(),
        operational_state=OperationalState(orders=4200, pending_orders=1250, workers=28, capacity_utilization=0.91),
        predictions=Predictions(workload="HIGH", workers_required=36, risk_score=0.82),
        alerts=[Alert(type="WORKER_SHORTAGE", severity="HIGH")]
    )
    state_manager.process_warehouse_update(wh_a_update)
    
    wh_b_update = WarehouseUpdate(
        warehouse_id="WH-B",
        timestamp=datetime.utcnow(),
        operational_state=OperationalState(orders=2800, pending_orders=500, workers=31, capacity_utilization=0.63),
        predictions=Predictions(workload="MEDIUM", workers_required=24, risk_score=0.31),
        alerts=[]
    )
    state_manager.process_warehouse_update(wh_b_update)
    
    return state_manager, comm_adapter, agent_graph

@pytest.mark.asyncio
async def test_worker_shortage_scenario(setup_agent):
    state_manager, comm_adapter, agent_graph = setup_agent
    
    initial_state = {
        "request_id": "req-1",
        "current_event": {"type": "WORKER_SHORTAGE", "warehouse_id": "WH-A"},
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
    
    config = {"configurable": {"thread_id": "req-1"}}
    
    # Run until interrupt (HumanApproval)
    async for output in agent_graph.astream(initial_state, config=config):
        pass
        
    state = agent_graph.get_state(config)
    
    # Assertions
    assert "WH-A" in state.values["affected_warehouses"]
    assert len(state.values["resource_shortages"]) > 0
    assert len(state.values["resource_surpluses"]) > 0
    
    recommendation = state.values["recommendation"]
    assert recommendation is not None
    assert recommendation["type"] == "WORKER_ALLOCATION"
    assert recommendation["source_warehouse"] == "WH-B"
    assert recommendation["target_warehouse"] == "WH-A"
    assert recommendation["quantity"] == 7
    assert recommendation["status"] == "PENDING_APPROVAL"
    assert state.values["approval_status"] == "PENDING_APPROVAL"
    
    # Simulate Approval
    agent_graph.update_state(config, {"approval_status": "APPROVED"}, as_node="HumanApproval")
    
    # Resume graph execution
    async for output in agent_graph.astream(None, config=config):
        pass
        
    final_state = agent_graph.get_state(config)
    
    # Verify execution
    execution_result = final_state.values.get("execution_result")
    assert execution_result is not None
    assert execution_result["status"] == "SUCCESS"
    
    assert len(comm_adapter.message_log) == 1
    msg = comm_adapter.message_log[0]
    assert msg["warehouse_id"] == "WH-B"
    assert msg["message_type"] == "RESOURCE_ALLOCATION_PROPOSAL"
    assert msg["payload"]["quantity"] == 7

@pytest.mark.asyncio
async def test_simulation_scenario(setup_agent):
    state_manager, comm_adapter, agent_graph = setup_agent
    
    initial_state = {
        "request_id": "req-2",
        "user_query": "What happens if demand at WH-A increases by 20%?",
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
    
    config = {"configurable": {"thread_id": "req-2"}}
    
    async for output in agent_graph.astream(initial_state, config=config):
        pass
        
    state = agent_graph.get_state(config)
    
    assert state.values["recommendation"] is not None
    assert state.values["recommendation"]["type"] == "SIMULATION"
    assert state.values["recommendation"]["status"] == "SIMULATION"
    assert "Simulated" in state.values["final_response"]

@pytest.mark.asyncio
async def test_inquiry_scenario(setup_agent):
    state_manager, comm_adapter, agent_graph = setup_agent
    
    initial_state = {
        "request_id": "req-3",
        "user_query": "Which warehouse currently needs attention and why?",
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
    
    config = {"configurable": {"thread_id": "req-3"}}
    
    async for output in agent_graph.astream(initial_state, config=config):
        pass
        
    state = agent_graph.get_state(config)
    
    assert state.values["final_response"] is not None
    assert "needs attention" in state.values["final_response"].lower()
    assert "WH-A" in state.values["final_response"]
