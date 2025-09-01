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
    if not settings.scheduler.price_stream or not settings.scheduler.price_stream.get("enabled"):
        return
    # TODO: implement OANDA pricing stream; on spikes route to risk adjustments only
    while True:
        print("Price stream loop (stub)")
        await asyncio.sleep(30)

async def macro_loop():
    if not settings.scheduler.macro_throttle or not settings.scheduler.macro_throttle.get("enabled"):
        return
    # TODO: query Trading Economics; set ALLOW_NEW_ENTRIES=false around events
    while True:
        print("Macro loop (stub)")
        await asyncio.sleep(300)

async def heartbeat_loop():
    while True:
        print(f"Heartbeat alive check at {dt.datetime.utcnow().isoformat()}")
        # TODO: check PnL, daily drawdown, open positions, etc.
        await asyncio.sleep(settings.scheduler.heartbeat_every_seconds)

async def run_scheduler():
    tasks = [
        bar_close_loops(),
        heartbeat_loop(),
    ]
    if settings.scheduler.price_stream and settings.scheduler.price_stream.get("enabled"):
        tasks.append(price_stream_loop())
    if settings.scheduler.macro_throttle and settings.scheduler.macro_throttle.get("enabled"):
        tasks.append(macro_loop())

    await asyncio.gather(*tasks)
