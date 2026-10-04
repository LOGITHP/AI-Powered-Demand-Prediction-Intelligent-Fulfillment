"""
Interactive query agent for the Head Office: a LangGraph ReAct loop where the
LLM decides which network tools to call, executes them, and synthesizes an
answer from real state.

    agent (LLM, tools bound)
      └─ has tool_calls? ──► tools ──► agent   (loop, capped by recursion_limit)
      └─ no tool calls ──► END
"""
import json
import logging
from typing import Annotated, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Head Office AI Agent orchestrating a network of warehouses.

You have tools to inspect live network state (per-warehouse orders, workers,
capacity utilization, risk), find worker shortages/surpluses, compare
warehouses, list active issues, and run what-if demand simulations.

Rules:
- ALWAYS call tools to ground your answer in live data instead of guessing.
- If asked to move/reallocate workers, you may only create a proposal with
  request_worker_allocation; a human manager approves it separately. Say so
  explicitly in your answer.
- Be concise and operational: lead with the answer, then the numbers that
  support it."""


class QueryState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tools_used: List[str]


def build_query_graph(llm, tools):
    """
    llm: a LangChain chat model (ChatNVIDIA). tools: list of LangChain tools.
    Returns (compiled_graph, tool_names) - the graph is stateless; pass the
    whole conversation via messages each call.
    """
    tool_registry = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: QueryState):
        response = llm_with_tools.invoke([SystemMessage(content=SYSTEM_PROMPT)] + state["messages"])
        return {"messages": [response]}

    def tools_node(state: QueryState):
        last = state["messages"][-1]
        responses = []
        used = []
        for tool_call in getattr(last, "tool_calls", None) or []:
            name = tool_call["name"]
            func = tool_registry.get(name)
            try:
                if func is None:
                    content = json.dumps({
                        "error": f"Unknown tool '{name}'. Available: {', '.join(tool_registry)}"
                    })
                else:
                    content = str(func.invoke(tool_call["args"]))
                used.append(name)
                logger.info("HO query tool %s -> ok", name)
            except Exception as exc:
                logger.exception("HO query tool %s failed", name)
                content = json.dumps({"error": f"Tool '{name}' failed: {exc}"})
            responses.append(ToolMessage(content=content, tool_call_id=tool_call["id"]))
        return {"messages": responses, "tools_used": used}

    def should_continue(state: QueryState):
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(QueryState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    return workflow.compile(), list(tool_registry)


def run_query(graph, query: str, recursion_limit: int = 20):
    """Run one user query through the graph. Returns (answer, tools_used)."""
    state = graph.invoke(
        {"messages": [HumanMessage(content=query)], "tools_used": []},
        config={"recursion_limit": recursion_limit},
    )
    answer = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, AIMessage)),
        "No answer produced.",
    )
    return answer, state.get("tools_used", [])
