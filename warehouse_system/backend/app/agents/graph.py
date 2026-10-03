import os
import json
from langgraph.graph import StateGraph, END
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.agents.state import WarehouseAgentState
from app.agents.tools import (
    get_warehouse_status, get_worker_status, get_outbound_status, get_inbound_status,
    run_labour_prediction, run_delay_prediction,
    recommend_worker_redistribution, request_manager_approval,
    send_worker_instruction, draft_notification, propose_reassignment
)
from app.core.config import settings

def load_nvidia_llm():
    if not settings.NVIDIA_API_KEY:
        raise ValueError("NVIDIA_API_KEY is not set.")
    return ChatNVIDIA(model=settings.NVIDIA_MODEL, api_key=settings.NVIDIA_API_KEY)

tools = [
    get_warehouse_status, get_worker_status, get_outbound_status, get_inbound_status,
    run_labour_prediction, run_delay_prediction,
    recommend_worker_redistribution, request_manager_approval,
    send_worker_instruction, draft_notification, propose_reassignment
]

# --- Explicit Nodes for the Warehouse Agent ---

def understand_request(state: WarehouseAgentState):
    llm = load_nvidia_llm()
    # Initial reasoning step
    messages = state.get("messages", [])
    if not messages:
        return {"messages": []}
        
    prompt = SystemMessage(content="You are the Warehouse Operations Agent. Understand the user's request. Output a single brief thought.")
    response = llm.invoke([prompt] + messages[-1:])
    return {"messages": [response]}

def call_operational_tools(state: WarehouseAgentState):
    # Bind tools and get LLM to call them
    llm = load_nvidia_llm().bind_tools(tools)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def execute_tools(state: WarehouseAgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_responses = []
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_func = {t.name: t for t in tools}.get(tool_name)
            if tool_func:
                result = tool_func.invoke(tool_args)
                from langchain_core.messages import ToolMessage
                tool_responses.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    
    return {"messages": tool_responses}

def detect_problems(state: WarehouseAgentState):
    # Optional node to analyze tool outputs
    return state

def generate_recommendation(state: WarehouseAgentState):
    # Let LLM generate final response
    llm = load_nvidia_llm()
    system_prompt = SystemMessage(content="""You are the Warehouse Operations Agent. 
Use the tool results to answer. 
Format response with STATUS, EVIDENCE, ISSUE, IMPACT, RECOMMENDATION, ACTION if analyzing operations.""")
    
    # If the last message was a tool message, or the last AI message had no tool calls, summarize
    response = llm.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}

def should_continue(state: WarehouseAgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return "generate_recommendation"

def check_approval(state: WarehouseAgentState):
    # Node to handle actions requiring approval
    return state

def sync_head_office(state: WarehouseAgentState):
    # Node to sync with head office API
    return state

def build_graph():
    workflow = StateGraph(WarehouseAgentState)
    
    # Add all required explicit nodes
    workflow.add_node("understand_request", understand_request)
    workflow.add_node("call_operational_tools", call_operational_tools)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("generate_recommendation", generate_recommendation)
    workflow.add_node("sync_head_office", sync_head_office)
    
    workflow.set_entry_point("understand_request")
    workflow.add_edge("understand_request", "call_operational_tools")
    
    # Decision Router
    workflow.add_conditional_edges(
        "call_operational_tools", 
        should_continue, 
        {
            "execute_tools": "execute_tools", 
            "generate_recommendation": "generate_recommendation"
        }
    )
    
    workflow.add_edge("execute_tools", "call_operational_tools")
    workflow.add_edge("generate_recommendation", "sync_head_office")
    workflow.add_edge("sync_head_office", END)
    
    return workflow.compile()
