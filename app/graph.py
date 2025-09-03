from __future__ import annotations
import asyncio
import json
import time
from typing import TypedDict, List, Optional
import datetime as dt

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda

from app.llm import make_llm
from app.settings import settings
from app.telemetry import tracer
from app.tools.risk_tool import guardrails_pass

# --- State Definition ---
class TraderState(TypedDict):
    messages: List
    error: Optional[str] = None

# --- Error Handling & Tools ---
def check_for_tool_error(state: TraderState) -> str:
    """Conditional edge to route to the error handler if a tool failed."""
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage) and last_message.content.startswith('{"error"'):
        tracer.log({"event_type": "error", "node": "check_for_tool_error", "error_message": last_message.content})
        return "error"
    return "continue"

@tool
async def get_candles(instrument: str, timeframe: str, count: int = 200) -> str:
    """Gets recent OHLC candles."""
    # ... (implementation is the same)
    try:
        if settings.data_provider == "mock":
            from app.tools import data_mock; df = data_mock.candles(instrument, timeframe, count=count)
        else:
            from app.tools import data_oanda; df = await data_oanda.candles(instrument, timeframe, count=count)
        if settings.broker_provider == "paper" and not df.empty:
            from app.tools.broker_paper import PaperBroker; PaperBroker().on_bar(instrument, float(df.iloc[-1].open), float(df.iloc[-1].high), float(df.iloc[-1].low), float(df.iloc[-1].close))
        return json.dumps(df.to_dict(orient="records"))
    except Exception as e:
        return json.dumps({"error": f"Failed to get candles: {e}"})

@tool
def execute_order(order: dict, open_positions: int = 0, daily_dd: float = 0.0, allow_new_entries: bool = True) -> str:
    """Executes an order."""
    # ... (implementation is the same)
    try:
        ok, reason = guardrails_pass(dt.datetime.now(dt.UTC), open_positions, daily_dd, allow_new_entries)
        if not ok: return json.dumps({"status": "skipped", "reason": reason})
        if settings.broker_provider == "paper":
            from app.tools.broker_paper import PaperBroker; result = PaperBroker().place_order(order)
        else:
            from app.tools import broker_oanda; result = asyncio.run(broker_oanda.place_order(order))
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Failed to execute order: {e}"})

# --- Graph Builder ---
def build_trader_graph(config: dict):
    llm = make_llm()

    # --- Tools ---
    @tool
    def propose_order(instrument: str, side: str, units: int, entry_type: str = "market", price: float | None = None):
        """Creates a normalized order proposal."""
        return {"instrument": instrument, "side": side, "units": int(units), "entry_type": entry_type, "price": price}

    @tool
    def attach_stops(order: dict, atr: float, sl_mult: float = None, tp_mult: float = None):
        """Attaches SL/TP to an order."""
        slm = sl_mult or settings.risk.sl_buffer_atr
        tpm = tp_mult or settings.risk.tp_buffer_atr
        o = order.copy()
        price = o.get("price")
        o["stop_loss"] = o.get("stop_loss") or (price - slm * atr if price else None)
        o["take_profit"] = o.get("take_profit") or (price + tpm * atr if price else None)
        return o

    # --- Agents ---
    strategy_agent = create_react_agent(
        llm,
        tools=[get_candles],
        name="strategy_agent",
        prompt="""You are the Strategy Selector. Your job is to analyze the market and decide on a trading strategy.
1. Call the `get_candles` tool to get the latest market data for the instrument and timeframe from the user's request.
2. Based on the candle data, choose a strategy preset from [trend_following, mean_reversion, breakout].
3. Return a JSON object with your chosen preset and a brief rationale. Example: {"preset": "trend_following", "rationale": "The 20-period EMA is above the 50-period EMA."}""",
    )

    signal_agent = create_react_agent(
        llm,
        tools=[propose_order],
        name="signal_agent",
        prompt="""You are the Signal Agent. Based on the strategy preset and candle data from the previous step, generate a trading signal.
Reply with a strict JSON object representing the signal. Example: {"action": "buy", "instrument": "EUR_USD", "timeframe": "M5", "units": 1000, "entry_type": "market", "price": null}.
If you decide not to trade, set the action to "hold".
If you decide to trade, call the `propose_order` tool with the signal details.""",
    )

    risk_agent = create_react_agent(
        llm,
        tools=[attach_stops],
        name="risk_agent",
        prompt="""You are the Risk Agent. Take the proposed order and attach stop_loss and take_profit levels based on the latest Average True Range (ATR) from the candle data.
Use the `attach_stops` tool to add these values to the order.
Reply with the final order JSON, including the calculated stop_loss and take_profit.""",
    )

    exec_agent = create_react_agent(
        llm,
        tools=[execute_order],
        name="exec_agent",
        prompt="""You are the Execution Agent. You will receive a final, risk-managed order.
Your job is to call the `execute_order` tool to place the trade with the broker.
If the tool returns an error or a "skipped" status, report it. Otherwise, confirm the successful execution.""",
    )

    # --- Traced Nodes ---
    def run_with_tracing(node_name: str, agent_runnable):
        def wrapper(state: TraderState):
            tracer.log({"event_type": "node_enter", "node": node_name, "input": state})
            start_time = time.monotonic()
            try:
                result = agent_runnable.invoke(state)
                latency_ms = (time.monotonic() - start_time) * 1000
                tracer.log({"event_type": "node_exit", "node": node_name, "output": result, "latency_ms": latency_ms, "status": "ok"})
                return result
            except Exception as e:
                latency_ms = (time.monotonic() - start_time) * 1000
                tracer.log({"event_type": "node_exit", "node": node_name, "error_message": str(e), "latency_ms": latency_ms, "status": "error"})
                raise
        return RunnableLambda(wrapper)

    def error_handler_node(state: TraderState) -> dict:
        tracer.log({"event_type": "node_enter", "node": "error_handler", "input": state})
        return {"error": "Terminating graph due to tool error."}

    # --- Graph ---
    graph = StateGraph(TraderState)
    graph.add_node("strategy", run_with_tracing("strategy", strategy_agent))
    graph.add_node("signal", run_with_tracing("signal", signal_agent))
    graph.add_node("risk", run_with_tracing("risk", risk_agent))
    graph.add_node("exec", run_with_tracing("exec", exec_agent))
    graph.add_node("error_handler", error_handler_node)

    graph.set_entry_point("strategy")
    graph.add_conditional_edges("strategy", check_for_tool_error, {"continue": "signal", "error": "error_handler"})
    graph.add_edge("signal", "risk")
    graph.add_edge("risk", "exec")
    graph.add_conditional_edges("exec", check_for_tool_error, {"continue": END, "error": "error_handler"})
    graph.add_edge("error_handler", END)

    return graph
