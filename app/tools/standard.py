from __future__ import annotations
import asyncio
import json
import datetime as dt

from langchain.tools import tool

from app.settings import settings
from app.tools.risk_tool import guardrails_pass

from app.tools.data_models import FeatureSummary

@tool
async def get_candles(instrument: str, timeframe: str, count: int = 200) -> str:
    """
    Gets a summary of recent market data, including the last N closes,
    technical indicators, and a digest of the features.
    """
    try:
        if settings.data.provider == "mock":
            from app.tools import data_mock; summary = data_mock.candles(instrument, timeframe, count=count)
        else:
            from app.tools import data_oanda; summary = await data_oanda.candles(instrument, timeframe, count=count)

        # This part for the paper broker is a bit of a hack.
        # It assumes the last bar's data can be read from the summary.
        # A better solution would be a proper event bus.
        if settings.broker_provider == "paper":
            from app.tools.broker_paper import PaperBroker
            # We need to read the parquet file to get the last bar for the paper broker
            # This is not ideal, but it's the only way to get the data without changing the tool's interface
            import pandas as pd
            df = pd.read_parquet(summary.cache_path)
            if not df.empty:
                 PaperBroker().on_bar(instrument, float(df.iloc[-1].open), float(df.iloc[-1].high), float(df.iloc[-1].low), float(df.iloc[-1].close))

        return summary.model_dump_json()
    except Exception as e:
        return json.dumps({"error": f"Failed to get candles: {e}"})

@tool
def execute_order(order: dict, open_positions: int = 0, daily_dd: float = 0.0, allow_new_entries: bool = True) -> str:
    """Executes an order."""
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
