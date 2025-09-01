from __future__ import annotations
import asyncio
import datetime as dt
from app.settings import settings
from app.tools import data_oanda
from app.graph import app as trader_graph

async def run_decision_cycle(instrument: str, timeframe: str):
    df = await data_oanda.candles(instrument, timeframe, count=400)
    if df.empty:
        return
    # Last bar already filtered by complete=True in provider
    await trader_graph.ainvoke({
        "messages": [
            {"role": "user", "content": f"CandleCloseEvent {instrument} {timeframe}"}
        ]
    })

async def bar_close_loops():
    while True:
        tasks = []
        for spec in settings.scheduler.decisions:
            tasks.append(run_decision_cycle(spec["instrument"], spec["timeframe"]))
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(20)  # lightweight polling; rely on complete flag

async def price_stream_loop():
    # TODO: implement OANDA pricing stream; on spikes route to risk adjustments only
    await asyncio.sleep(1)
    while True:
        await asyncio.sleep(5)

async def macro_loop():
    # TODO: query Trading Economics; set ALLOW_NEW_ENTRIES=false around events
    await asyncio.sleep(1)
    while True:
        await asyncio.sleep(300)

async def heartbeat_loop():
    while True:
        # TODO: check PnL, daily drawdown, open positions, etc.
        await asyncio.sleep(settings.scheduler.heartbeat_every_seconds)

async def run_scheduler():
    await asyncio.gather(
        bar_close_loops(),
        price_stream_loop(),
        macro_loop(),
        heartbeat_loop(),
    )
