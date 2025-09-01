from __future__ import annotations
import asyncio
from typing import TypedDict, List
import pandas as pd

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool

from app.llm import make_llm
from app.settings import settings
from app.tools.risk_tool import guardrails_pass

# --- State Definition ---
class TraderState(TypedDict):
    messages: List
    instrument: str
    timeframe: str
    candles: pd.DataFrame
    # ... other state fields can be added here

# --- Nodes ---
def handle_event(state: TraderState) -> TraderState:
    """
    Entry node: Parses the input event, fetches data, and steps the paper broker.
    """
    print("--- handling event ---")
    last_message = state["messages"][-1]

    # Parse instrument and timeframe from the event message
    parts = last_message['content'].split(" ")
    instrument = parts[1]
    timeframe = parts[2]

    # Fetch candle data
    if settings.data_provider == "mock":
        from app.tools import data_mock
        df = data_mock.candles(instrument, timeframe, count=200)
    else:
        from app.tools import data_oanda
        # Running async code in a sync function
        df = asyncio.run(data_oanda.candles(instrument, timeframe, count=200))

    # Step paper broker if enabled
    if settings.broker_provider == "paper" and not df.empty:
        from app.tools.broker_paper import PaperBroker
        last_bar = df.iloc[-1]
        PaperBroker().on_bar(
            instrument,
            float(last_bar.open), float(last_bar.high), float(last_bar.low), float(last_bar.close)
        )

    print(f"--- fetched {len(df)} candles for {instrument} {timeframe} ---")

    return {
        **state,
        "instrument": instrument,
        "timeframe": timeframe,
        "candles": df.to_dict(orient="records"), # Pass serializable data
    }

# --- Graph Builder ---
def build_trader_graph(config: dict):

    llm = make_llm()

    # --- Tools ---
    @tool
    def propose_order(instrument: str, side: str, units: int, entry_type: str = "market", price: float | None = None):
        """Create a normalized order proposal."""
        return {
            "instrument": instrument,
            "side": side,
            "units": int(units),
            "entry_type": entry_type,
            "price": price,
            "stop_loss": None,
            "take_profit": None,
        }

    @tool
    def attach_stops(order: dict, atr: float, sl_mult: float = None, tp_mult: float = None):
        """Attach SL/TP using ATR multiples from config if not supplied."""
        slm = sl_mult or settings.risk.sl_buffer_atr
        tpm = tp_mult or settings.risk.tp_buffer_atr
        o = order.copy()
        price = o.get("price")
        o["stop_loss"] = o.get("stop_loss") or (price - slm * atr if price else None)
        o["take_profit"] = o.get("take_profit") or (price + tpm * atr if price else None)
        return o

    @tool
    def execute_order(order: dict, open_positions: int = 0, daily_dd: float = 0.0, allow_new_entries: bool = True):
        """Execute order via broker if guardrails pass; else return skip reason."""
        import datetime as dt
        ok, reason = guardrails_pass(dt.datetime.now(dt.UTC), open_positions, daily_dd, allow_new_entries)
        if not ok:
            return {"status": "skipped", "reason": reason}

        if str(settings.mode).upper() == "BACKTEST":
            return {"status": "skipped", "reason": "backtest_mode"}

        if settings.broker_provider == "paper":
            from app.tools.broker_paper import PaperBroker
            return PaperBroker().place_order(order)
        else:
            from app.tools import broker_oanda
            return asyncio.run(broker_oanda.place_order(order))

    # --- Agents ---
    strategy_agent = create_react_agent(
        llm,
        tools=[], # No tools needed, gets data from state
        name="strategy_agent",
        prompt="""You are the Strategy Selector. Based on the provided candle data, choose a preset from [trend_following, mean_reversion, breakout].
The candle data is available in the input. Do not try to fetch it.
Return JSON: {"preset": str, "rationale": str}.""",
    )

    signal_agent = create_react_agent(
        llm,
        tools=[propose_order], # Only needs to propose an order
        name="signal_agent",
        prompt="""Generate a trading signal based on the latest candle data and the chosen strategy preset.
The candle data is in the input. Do not try to fetch it.
Reply strict JSON: {"action": "buy|sell|hold", "instrument": str, "timeframe": str, "units": int, "entry_type": "market|limit", "price": float|None}.
If hold, stop. If buy/sell, call propose_order.""",
    )

    risk_agent = create_react_agent(
        llm,
        tools=[attach_stops],
        name="risk_agent",
        prompt="""Given an order proposal and ATR, attach stop_loss and take_profit using multiples.
Reply final order JSON.""",
    )

    exec_agent = create_react_agent(
        llm,
        tools=[execute_order],
        name="exec_agent",
        prompt="""Execute the validated order if allowed. Return broker response JSON or skip reason.""",
    )

    # --- Graph Definition ---
    graph = StateGraph(TraderState)

    graph.add_node("event_handler", handle_event)
    graph.add_node("strategy", strategy_agent)
    graph.add_node("signal", signal_agent)
    graph.add_node("risk", risk_agent)
    graph.add_node("exec", exec_agent)

    graph.add_edge(START, "event_handler")
    graph.add_edge("event_handler", "strategy")
    graph.add_edge("strategy", "signal")
    graph.add_edge("signal", "risk")
    graph.add_edge("risk", "exec")
    graph.add_edge("exec", END)

    return graph
