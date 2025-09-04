from __future__ import annotations
import time
from typing import TypedDict, List, Optional
from functools import wraps
import random
import httpx
import json

from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import ToolMessage

from app.llm import make_llm, SUPPORTS_TOOL_CALLING
from app.prompts import prompt_registry
from app.settings import settings
from app.telemetry import tracer

# --- State Definition ---
class TraderState(TypedDict):
    messages: List
    error: Optional[str] = None

# --- Tracing & Error Handling ---
def create_traced_node(node_name: str, prompt_id: str, agent_runnable):
    def wrapper(state: TraderState):
        prompt = prompt_registry.get(prompt_id)
        tracer.log({"event_type": "node_enter", "node": node_name, "input": state, "prompt_id": prompt.id, "prompt_version": prompt.meta.get("version")})

        last_exception = None
        for attempt in range(2):
            start_time = time.monotonic()
            try:
                result = agent_runnable.invoke(state)
                latency_ms = (time.monotonic() - start_time) * 1000

                log_payload = {"event_type": "node_exit", "node": node_name, "output": result, "latency_ms": latency_ms, "status": "ok", "attempt": attempt + 1}

                # For strategy node, extract audit fields from the output
                if node_name == "strategy" and result.get("messages"):
                    try:
                        content = result["messages"][-1].content
                        if isinstance(content, str):
                            data = json.loads(content)
                            log_payload["features_digest"] = data.get("features_digest")
                            log_payload["cache_path"] = data.get("cache_path")
                    except (json.JSONDecodeError, IndexError):
                        pass # Ignore if parsing fails

                tracer.log(log_payload)
                return result
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                latency_ms = (time.monotonic() - start_time) * 1000
                last_exception = e
                print(f"Attempt {attempt + 1} failed for node {node_name}: {type(e).__name__}. Retrying...")
                tracer.log({
                    "event_type": "node_retry", "node": node_name, "error_type": type(e).__name__,
                    "error_message": str(e), "latency_ms": latency_ms, "attempt": attempt + 1
                })
                time.sleep(random.uniform(0.3, 0.7)) # Jitter
            except Exception as e:
                last_exception = e
                break # Don't retry on other exceptions

        # If all retries fail or a non-retriable exception occurs
        latency_ms = (time.monotonic() - start_time) * 1000
        error_details = {
            "event_type": "node_exit",
            "node": node_name,
            "error_type": type(last_exception).__name__,
            "error_message": str(last_exception),
            "latency_ms": latency_ms,
            "status": "error",
            "llm_base_url": settings.llm.base_url,
            "llm_model": settings.llm.model,
            "attempts": 2
        }
        tracer.log(error_details)
        raise last_exception
    return RunnableLambda(wrapper)

def error_handler_node(state: TraderState) -> dict:
    tracer.log({"event_type": "node_enter", "node": "error_handler", "input": state})
    return {"error": "Terminating graph due to tool error."}

def check_for_tool_error(state: TraderState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage) and last_message.content.startswith('{"error"'):
        tracer.log({"event_type": "error", "node": "check_for_tool_error", "error_message": last_message.content})
        return "error"
    return "continue"

def strategy_router(state: TraderState) -> str:
    """The router for the strategy node, with special handling for dry runs."""
    if state["messages"][-1].content == "DryRunEvent":
        return END
    return check_for_tool_error(state)

# --- Graph Builder ---
def build_trader_graph(
    config: dict,
    tools: Optional[List[BaseTool]] = None,
    route_overrides: Optional[dict] = None
):
    if tools is None:
        from app.tools.registry import get_toolset
        tools = get_toolset()

    # Set up default routers or use overrides
    routers = {
        "strategy": strategy_router,
        "signal": check_for_tool_error,
        "risk": check_for_tool_error,
        "exec": check_for_tool_error,
    }
    if route_overrides:
        routers.update(route_overrides)

    strategy_tools = [t for t in tools if t.name == "get_candles"]
    signal_tools = [t for t in tools if t.name == "propose_order"]
    risk_tools = [t for t in tools if t.name == "attach_stops"]
    exec_tools = [t for t in tools if t.name == "execute_order"]

    llm = make_llm()

    # --- Agents ---
    if not SUPPORTS_TOOL_CALLING and settings.llm.require_tools:
        raise ValueError("Tool calling is required by settings, but the configured LLM does not support it.")

    strategy_agent = create_react_agent(llm, tools=strategy_tools, prompt=prompt_registry.get("strategy/decide_strategy__v1").body)
    signal_agent = create_react_agent(llm, tools=signal_tools, prompt=prompt_registry.get("signal/generate_signal__v1").body)
    risk_agent = create_react_agent(llm, tools=risk_tools, prompt=prompt_registry.get("risk/assess_risk__v1").body)
    exec_agent = create_react_agent(llm, tools=exec_tools, prompt=prompt_registry.get("exec/execute_order__v1").body)

    # --- Graph ---
    graph = StateGraph(TraderState)
    graph.add_node("strategy", create_traced_node("strategy", "strategy/decide_strategy__v1", strategy_agent))
    graph.add_node("signal", create_traced_node("signal", "signal/generate_signal__v1", signal_agent))
    graph.add_node("risk", create_traced_node("risk", "risk/assess_risk__v1", risk_agent))
    graph.add_node("exec", create_traced_node("exec", "exec/execute_order__v1", exec_agent))
    graph.add_node("error_handler", error_handler_node)

    graph.set_entry_point("strategy")
    graph.add_conditional_edges("strategy", routers["strategy"], {"continue": "signal", "error": "error_handler", END: END})
    graph.add_conditional_edges("signal", routers["signal"], {"continue": "risk", "error": "error_handler"})
    graph.add_conditional_edges("risk", routers["risk"], {"continue": "exec", "error": "error_handler"})
    graph.add_conditional_edges("exec", routers["exec"], {"continue": END, "error": "error_handler"})
    graph.add_edge("error_handler", END)

    return graph
