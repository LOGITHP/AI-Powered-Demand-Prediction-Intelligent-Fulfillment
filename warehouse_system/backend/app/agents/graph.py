import os
from langgraph.graph import StateGraph, END
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage
from app.agents.state import WarehouseAgentState
from app.agents.tools import (
    get_warehouse_status, get_worker_status, get_outbound_status,
    run_labour_prediction, run_delay_prediction,
    recommend_worker_redistribution, request_manager_approval
)
from app.core.config import settings

def load_nvidia_llm():
    if not settings.NVIDIA_API_KEY:
        raise ValueError("NVIDIA_API_KEY is not set.")
    return ChatNVIDIA(model=settings.NVIDIA_MODEL, api_key=settings.NVIDIA_API_KEY)

tools = [
    get_warehouse_status, get_worker_status, get_outbound_status,
    run_labour_prediction, run_delay_prediction,
    recommend_worker_redistribution, request_manager_approval
]

def agent_node(state: WarehouseAgentState):
    llm = load_nvidia_llm().bind_tools(tools)
    messages = state.get("messages", [])
    response = llm.invoke(messages)
    return {"messages": [response]}

def execute_tools(state: WarehouseAgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_responses = []
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            # Simple dispatcher
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            tool_func = {t.name: t for t in tools}.get(tool_name)
            if tool_func:
                result = tool_func.invoke(tool_args)
                from langchain_core.messages import ToolMessage
                tool_responses.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    
    return {"messages": tool_responses}

def should_continue(state: WarehouseAgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END

def build_graph():
    workflow = StateGraph(WarehouseAgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", execute_tools)
    
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()
