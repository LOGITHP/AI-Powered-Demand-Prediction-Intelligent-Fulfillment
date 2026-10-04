import json
import logging
import threading

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenAI

from app.agents.state import WarehouseAgentState
from app.agents.tools import (
    get_warehouse_status, get_worker_status, get_outbound_status, get_inbound_status,
    run_labour_prediction, run_delay_prediction,
    recommend_worker_redistribution, request_manager_approval,
    send_worker_instruction, draft_notification, propose_reassignment,
    add_new_employee
)
from app.core.config import settings

logger = logging.getLogger(__name__)

TOOLS = [
    get_warehouse_status, get_worker_status, get_outbound_status, get_inbound_status,
    run_labour_prediction, run_delay_prediction,
    recommend_worker_redistribution, request_manager_approval,
    send_worker_instruction, draft_notification, propose_reassignment, add_new_employee
]

TOOL_REGISTRY = {t.name: t for t in TOOLS}

# ChatGoogleGenAI clients are thread-safe for invoke; cache one per process instead
# of rebuilding (with a new HTTPS session) inside every graph node.
_llm_cache = {}
_llm_lock = threading.Lock()


def load_nvidia_llm(bind_tools=False):
    import os
    api_key = os.environ.get("GOOGLE_API_KEY")
    key = "bound" if bind_tools else "plain"
    with _llm_lock:
        if key not in _llm_cache:
            llm = ChatGoogleGenAI(model="gemini-1.5-flash", google_api_key=api_key)
            if bind_tools:
                llm = llm.bind_tools(TOOLS)
            _llm_cache[key] = llm
    return _llm_cache[key]


# Explicit nodes for the Warehouse Agent

def understand_request(state: WarehouseAgentState):
    llm = load_nvidia_llm()
    messages = state.get("messages", [])
    if not messages:
        return {"messages": []}

    prompt = SystemMessage(content=(
        "You are the Warehouse Operations Agent. Understand the user's request. "
        "When instructing workers (e.g., via send_worker_instruction), you MUST include a detailed, step-by-step list of the work they must do in that day. Never just say 'assigned'. "
        "You have tools to check ML predictions and add new employees (add_new_employee). If the user asks you to add an employee and see how it affects ML predictions, add the employee first, then run the ML prediction tools. "
        "Output a single brief thought."
    ))
    response = llm.invoke([prompt] + messages[-1:])
    return {"messages": [response]}


def call_operational_tools(state: WarehouseAgentState):
    llm = load_nvidia_llm(bind_tools=True)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def execute_tools(state: WarehouseAgentState):
    """
    Execute every requested tool call. Each call is isolated: a failing or
    unknown tool becomes an error ToolMessage so the LLM can recover and
    answer, instead of the whole graph crashing.
    """
    messages = state["messages"]
    last_message = messages[-1]

    tool_responses = []
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_func = TOOL_REGISTRY.get(tool_name)
            try:
                if tool_func is None:
                    result = json.dumps({
                        "error": f"Unknown tool '{tool_name}'. "
                                 f"Available tools: {', '.join(TOOL_REGISTRY)}"
                    })
                else:
                    result = str(tool_func.invoke(tool_args))
                logger.info("Agent tool %s(%s) -> ok", tool_name, tool_args)
            except Exception as exc:
                logger.exception("Agent tool %s failed", tool_name)
                result = json.dumps({"error": f"Tool '{tool_name}' failed: {exc}"})
            tool_responses.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    return {"messages": tool_responses}


def generate_recommendation(state: WarehouseAgentState):
    llm = load_nvidia_llm()
    system_prompt = SystemMessage(content="""You are the Warehouse Operations Agent.
Use the tool results to answer. If a tool returned an error, say so and answer with what you have.
When instructing workers (e.g., via send_worker_instruction), you MUST include a detailed, step-by-step list of the work they must do in that day. Never just say 'assigned' or 'called'.
If the user asks you to add an employee and check ML predictions, remember that average_worker_skill and average_worker_experience drive the ML output. Add the employee first, then re-run the ML predictions.
Format response with STATUS, EVIDENCE, ISSUE, IMPACT, RECOMMENDATION, ACTION if analyzing operations.""")
    response = llm.invoke([system_prompt] + state["messages"])
    return {"messages": [response]}


def should_continue(state: WarehouseAgentState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "execute_tools"
    return "generate_recommendation"


def sync_head_office(state: WarehouseAgentState):
    # Head-office state sync happens via the background task in app.main;
    # nothing to do per-chat here yet.
    return state


def build_graph():
    workflow = StateGraph(WarehouseAgentState)

    workflow.add_node("understand_request", understand_request)
    workflow.add_node("call_operational_tools", call_operational_tools)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("generate_recommendation", generate_recommendation)
    workflow.add_node("sync_head_office", sync_head_office)

    workflow.set_entry_point("understand_request")
    workflow.add_edge("understand_request", "call_operational_tools")

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
