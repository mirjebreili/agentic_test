from __future__ import annotations
import asyncio
import datetime as dt
from app.settings import settings
from app.graph import app as trader_graph

async def run_decision_cycle(instrument: str, timeframe: str):
    # pick data provider
    if settings.data_provider == "mock":
        from app.tools import data_mock
        df = data_mock.candles(instrument, timeframe, count=2)
    else:
        from app.tools import data_oanda
        df = await data_oanda.candles(instrument, timeframe, count=2)

    if df.empty:
        return

    last = df.iloc[-1]

    # advance paper broker per bar
    if settings.broker_provider == "paper":
        from app.tools.broker_paper import PaperBroker
        PaperBroker().on_bar(
            instrument,
            float(last.open), float(last.high), float(last.low), float(last.close)
        )

    # trigger the agent chain on bar close
    await trader_graph.ainvoke({
        "messages":[{"role":"user","content":f"CandleCloseEvent {instrument} {timeframe}"}]
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
        await asyncio.sleep(30)

async def macro_loop():
    if not settings.scheduler.macro_throttle or not settings.scheduler.macro_throttle.get("enabled"):
        return
    # TODO: query Trading Economics; set ALLOW_NEW_ENTRIES=false around events
    while True:
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
