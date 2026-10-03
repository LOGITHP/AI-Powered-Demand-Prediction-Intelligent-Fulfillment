from datetime import datetime
from typing import Dict, Any
from agent.state import AgentState
from state.manager import StateManager
from tools.resource_tools import ResourceTools
from tools.network_tools import NetworkTools
from communication.interface import CommunicationAdapter, MessageType
from providers.llm import LLMProvider
from providers.optimization import OptimizationProvider
import json

class AgentNodes:
    def __init__(
        self, 
        state_manager: StateManager,
        resource_tools: ResourceTools,
        network_tools: NetworkTools,
        comm_adapter: CommunicationAdapter,
        llm: LLMProvider,
        optimizer: OptimizationProvider
    ):
        self.state_manager = state_manager
        self.resource_tools = resource_tools
        self.network_tools = network_tools
        self.comm_adapter = comm_adapter
        self.llm = llm
        self.optimizer = optimizer

    def receive_request(self, state: AgentState) -> AgentState:
        state["timestamps"]["receive_request"] = datetime.utcnow().isoformat()
        return state

    def observe_network(self, state: AgentState) -> AgentState:
        state["network_state"] = self.network_tools.get_network_state()
        state["timestamps"]["observe_network"] = datetime.utcnow().isoformat()
        return state

    def analyze_situation(self, state: AgentState) -> AgentState:
        # Determine problems from current_event or query
        problems = []
        shortages = []
        
        event = state.get("current_event")
        query = state.get("user_query")
        
        if event and event.get("event_type") == "WORKER_SHORTAGE":
            wh_id = event["warehouse_id"]
            problems.append(f"{wh_id} is experiencing a worker shortage.")
            state["affected_warehouses"].append(wh_id)
            
            # Use tools to find exact shortage
            wh_shortages = self.resource_tools.find_resource_shortage("workers")
            shortages = [s for s in wh_shortages if s["warehouse_id"] == wh_id]
            
        elif query:
            if "demand" in query.lower() and "increase" in query.lower():
                from tools.simulation_tools import SimulationTools
                st = SimulationTools(self.state_manager)
                scenario = {
                    "warehouse": "WH-A",
                    "demand_change_percent": 20
                }
                sim_result = st.simulate_action(scenario)
                state["recommendation"] = {
                    "type": "SIMULATION",
                    "result": sim_result,
                    "status": "SIMULATION"
                }
                state["final_response"] = f"Simulation complete. {sim_result.get('impact_analysis')}"
                
            elif "needs attention" in query.lower():
                network_state = self.network_tools.get_network_state()
                high_risk = []
                for wh_id, data in network_state.get("warehouses", {}).items():
                    if data.get("risk_score", 0) > 0.8:
                        high_risk.append(wh_id)
                
                if high_risk:
                    state["final_response"] = f"Warehouse(s) {', '.join(high_risk)} needs attention due to high risk score."
                else:
                    state["final_response"] = "No warehouses currently need critical attention."
            
        state["identified_problems"] = problems
        state["resource_shortages"] = shortages
        state["timestamps"]["analyze_situation"] = datetime.utcnow().isoformat()
        return state

    def determine_required_tools(self, state: AgentState) -> AgentState:
        # If we have a shortage, we need to find surplus
        if state["resource_shortages"]:
            state["tool_calls"].append({"tool": "find_resource_surplus", "args": {"resource_type": "workers"}})
        return state

    def tool_execution(self, state: AgentState) -> AgentState:
        for call in state["tool_calls"]:
            if call["tool"] == "find_resource_surplus":
                surpluses = self.resource_tools.find_resource_surplus(**call["args"])
                state["tool_results"].append({"tool": call["tool"], "result": surpluses})
                state["resource_surpluses"] = surpluses
        # Clear tool calls after execution
        state["tool_calls"] = []
        return state

    def generate_action_plan(self, state: AgentState) -> AgentState:
        # Check if we have shortages and surpluses
        if state["resource_shortages"] and state["resource_surpluses"]:
            # Mock Optimization Provider call
            opt_result = self.optimizer.optimize_worker_allocation(
                network_state=state["network_state"],
                constraints=[]
            )
            
            if opt_result.get("allocations"):
                alloc = opt_result["allocations"][0]
                plan = self.resource_tools.create_resource_allocation_plan(
                    source=alloc["source"],
                    target=alloc["target"],
                    quantity=alloc["quantity"]
                )
                
                # Combine info to reasoning
                reasoning = [
                    f"{alloc['target']} requires additional workforce",
                    f"{alloc['source']} has potentially available workforce"
                ]
                
                state["recommendation"] = {
                    "type": "WORKER_ALLOCATION",
                    "source_warehouse": alloc["source"],
                    "target_warehouse": alloc["target"],
                    "quantity": alloc["quantity"],
                    "reason": reasoning,
                    "status": "PENDING_APPROVAL"
                }
                state["candidate_actions"].append(state["recommendation"])
        return state

    def validate_action(self, state: AgentState) -> AgentState:
        # In a real scenario, this would check constraints
        state["validation_result"] = {"is_valid": True, "notes": "Constraints satisfied"}
        rec = state.get("recommendation")
        if rec and rec.get("status") != "SIMULATION":
            state["approval_status"] = "PENDING_APPROVAL"
        return state

    def human_approval(self, state: AgentState) -> Dict[str, Any]:
        # This is a dummy node, LangGraph interrupt will happen before this or here
        # When resumed, the state will have been updated externally with APPROVED or REJECTED
        return {}

    def execute_action(self, state: AgentState) -> AgentState:
        if state.get("approval_status") == "APPROVED" and state.get("recommendation"):
            rec = state["recommendation"]
            if rec["type"] == "WORKER_ALLOCATION":
                response = self.comm_adapter.send_message_to_warehouse(
                    warehouse_id=rec["source_warehouse"],
                    message_type=MessageType.RESOURCE_ALLOCATION_PROPOSAL,
                    payload={
                        "target": rec["target_warehouse"],
                        "quantity": rec["quantity"]
                    }
                )
                state["execution_result"] = response
        return state
        
    def update_state(self, state: AgentState) -> AgentState:
        if state.get("execution_result") and state["execution_result"].get("status") == "SUCCESS":
            # Real implementation would wait for actual ACTION_RESULT event, 
            # here we mock state update for demonstration
            pass
        return state

    def explain(self, state: AgentState) -> AgentState:
        if state.get("final_response"):
            return state
            
        if state.get("recommendation"):
            # Use LLM to explain the recommendation
            decision_data = state["recommendation"]
            explanation = self.llm.generate_explanation(decision_data)
            state["final_response"] = explanation
        else:
            state["final_response"] = "No actions recommended."
        return state
