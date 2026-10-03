from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent.state import AgentState
from agent.nodes import AgentNodes

def build_head_office_graph(nodes: AgentNodes) -> StateGraph:
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("ReceiveRequest", nodes.receive_request)
    workflow.add_node("ObserveNetwork", nodes.observe_network)
    workflow.add_node("AnalyzeSituation", nodes.analyze_situation)
    workflow.add_node("DetermineRequiredTools", nodes.determine_required_tools)
    workflow.add_node("ToolExecution", nodes.tool_execution)
    workflow.add_node("GenerateActionPlan", nodes.generate_action_plan)
    workflow.add_node("ValidateAction", nodes.validate_action)
    workflow.add_node("HumanApproval", nodes.human_approval)
    workflow.add_node("ExecuteAction", nodes.execute_action)
    workflow.add_node("UpdateState", nodes.update_state)
    workflow.add_node("Explain", nodes.explain)
    
    # Define edges
    workflow.set_entry_point("ReceiveRequest")
    workflow.add_edge("ReceiveRequest", "ObserveNetwork")
    workflow.add_edge("ObserveNetwork", "AnalyzeSituation")
    workflow.add_edge("AnalyzeSituation", "DetermineRequiredTools")
    
    # Conditional edge for tool execution
    def need_tools(state: AgentState):
        if state.get("tool_calls"):
            return "ToolExecution"
        return "GenerateActionPlan"
        
    workflow.add_conditional_edges(
        "DetermineRequiredTools",
        need_tools,
        {
            "ToolExecution": "ToolExecution",
            "GenerateActionPlan": "GenerateActionPlan"
        }
    )
    
    # After tools, we might need more tools or go to planning
    workflow.add_edge("ToolExecution", "GenerateActionPlan")
    
    workflow.add_edge("GenerateActionPlan", "ValidateAction")
    
    # Conditional edge for approval
    def routing_after_validation(state: AgentState):
        if state.get("approval_status") == "PENDING_APPROVAL":
            return "HumanApproval"
        return "Explain"
        
    workflow.add_conditional_edges(
        "ValidateAction",
        routing_after_validation,
        {
            "HumanApproval": "HumanApproval",
            "Explain": "Explain"
        }
    )
    
    # From human approval, branch on status
    def routing_after_approval(state: AgentState):
        status = state.get("approval_status")
        if status == "APPROVED":
            return "ExecuteAction"
        return "Explain" # If rejected, just explain
        
    workflow.add_conditional_edges(
        "HumanApproval",
        routing_after_approval,
        {
            "ExecuteAction": "ExecuteAction",
            "Explain": "Explain"
        }
    )
    
    workflow.add_edge("ExecuteAction", "UpdateState")
    workflow.add_edge("UpdateState", "Explain")
    workflow.add_edge("Explain", END)
    
    # Compile with checkpointer for human-in-the-loop
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["HumanApproval"])
