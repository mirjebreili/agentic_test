from __future__ import annotations
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
import asyncio
from app.llm import make_llm
from app.settings import settings
from app.tools import data_oanda, broker_oanda
from app.tools.risk_tool import guardrails_pass

llm = make_llm()

# ---- Tools exposed to agents ----
@tool
def get_candles(instrument: str, timeframe: str, count: int = 400):
    """Return recent OHLC candles for an FX instrument and timeframe."""
    df = asyncio.run(data_oanda.candles(instrument, timeframe, count))
    return df.to_dict(orient="records")

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
    price = o.get("price")  # for market we might not have it; stub handled by broker
    # Note: Fill precise SL/TP off current price server-side if needed.
    o["stop_loss"] = o.get("stop_loss") or (price - slm * atr if price else None)
    o["take_profit"] = o.get("take_profit") or (price + tpm * atr if price else None)
    return o

@tool
def execute_order(order: dict, open_positions: int = 0, daily_dd: float = 0.0, allow_new_entries: bool = True):
    """Execute order via broker if guardrails pass; else return skip reason."""
    import datetime as dt
    ok, reason = guardrails_pass(dt.datetime.utcnow(), open_positions, daily_dd, allow_new_entries)
    if not ok:
        return {"status": "skipped", "reason": reason}
    if str(settings.mode).upper() == "BACKTEST":
        return {"status": "skipped", "reason": "backtest_mode"}
    res = asyncio.run(broker_oanda.place_order(order))
    return res

# ---- Agents (light prompts; can be replaced by your custom ones) ----
strategy_agent = create_react_agent(
    llm,
    tools=[get_candles],
    name="strategy_agent",
    prompt=(
        "Choose preset from [trend_following, mean_reversion, breakout] based on candles.\\n"
        "Return JSON: {\\"preset\\": str, \\"rationale\\": str}."
    ),
)

signal_agent = create_react_agent(
    llm,
    tools=[get_candles, propose_order],
    name="signal_agent",
    prompt=(
        "Generate a signal JSON: {action: buy|sell|hold, instrument, timeframe, units, entry_type, price|null}.\\n"
        "If hold, stop. If buy/sell, call propose_order."
    ),
)

risk_agent = create_react_agent(
    llm,
    tools=[attach_stops],
    name="risk_agent",
    prompt=(
        "Given an order proposal and ATR, attach stop_loss and take_profit using multiples.\\n"
        "Reply final order JSON."
    ),
)

exec_agent = create_react_agent(
    llm,
    tools=[execute_order],
    name="exec_agent",
    prompt=(
        "Execute the validated order if allowed. Return broker response JSON or skip reason."
    ),
)

class TraderState(MessagesState):
    pass

graph = StateGraph(TraderState)

graph.add_node("strategy", strategy_agent)
graph.add_node("signal",   signal_agent)
graph.add_node("risk",     risk_agent)
graph.add_node("exec",     exec_agent)

graph.add_edge(START, "strategy")
graph.add_edge("strategy", "signal")
graph.add_edge("signal", "risk")
graph.add_edge("risk", "exec")
graph.add_edge("exec", END)

app = graph.compile()
