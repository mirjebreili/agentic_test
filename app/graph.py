from __future__ import annotations
import asyncio
from typing import TypedDict, List

from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool

from app.llm import make_llm
from app.settings import settings
from app.tools.risk_tool import guardrails_pass

# --- Tools ---
@tool
async def get_candles(instrument: str, timeframe: str, count: int = 200):
    """
    Asynchronously get recent OHLC candles for an FX instrument and timeframe.
    This tool will use the data provider specified in the config (mock or oanda).
    """
    if settings.data_provider == "mock":
        from app.tools import data_mock
        df = data_mock.candles(instrument, timeframe, count=count)
    else:
        from app.tools import data_oanda
        df = await data_oanda.candles(instrument, timeframe, count=count)

    # Also step the paper broker if it's active
    if settings.broker_provider == "paper" and not df.empty:
        from app.tools.broker_paper import PaperBroker
        last_bar = df.iloc[-1]
        PaperBroker().on_bar(
            instrument,
            float(last_bar.open), float(last_bar.high), float(last_bar.low), float(last_bar.close)
        )

    return df.to_dict(orient="records")

# --- Graph Builder ---
def build_trader_graph(config: dict):

    llm = make_llm()

    # --- Tools (specific to this graph) ---
    @tool
    def propose_order(instrument: str, side: str, units: int, entry_type: str = "market", price: float | None = None):
        """Create a normalized order proposal."""
        return {"instrument": instrument, "side": side, "units": int(units), "entry_type": entry_type, "price": price, "stop_loss": None, "take_profit": None}

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
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(broker_oanda.place_order(order))

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

    # --- Graph Definition ---
    graph = StateGraph(MessagesState)

    graph.add_node("strategy", strategy_agent)
    graph.add_node("signal", signal_agent)
    graph.add_node("risk", risk_agent)
    graph.add_node("exec", exec_agent)

    graph.set_entry_point("strategy")
    graph.add_edge("strategy", "signal")
    graph.add_edge("signal", "risk")
    graph.add_edge("risk", "exec")
    graph.add_edge("exec", END)

    return graph
