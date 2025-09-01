from __future__ import annotations
import os
from langgraph_sdk import get_sync_client  # pip install langgraph-sdk

# Configure the local server URL
URL = os.environ.get("LG_URL", "http://127.0.0.1:2024")
client = get_sync_client(url=URL)  # no API key needed for dev/inmem

# 1) Find the default assistant for our graph "trader"
# When the server loads your graph, it creates a default assistant for each graph.
assistants = client.assistants.search()  # list
trader = next((a for a in assistants if a.get("graph") == "trader"), None)
if not trader:
    raise SystemExit("No assistant for graph 'trader' found. Did the server load the graph?")

assistant_id = trader["assistant_id"]

def upsert_cron(name: str, schedule: str, instrument: str, timeframe: str):
    # Input payload your graph expects; adjust as needed
    the_input = {
        "messages": [
            {"role": "user", "content": f"CandleCloseEvent {instrument} {timeframe}"}
        ],
        # Optional: pass run-time config into nodes
        "config": {"configurable": {"instrument": instrument, "timeframe": timeframe}}
    }

    # Create (or replace) a cron with given name/schedule
    # Some SDKs require unique names or we check existing crons by metadata.
    crons = client.crons.search()
    existing = next((c for c in crons if c.get("name") == name), None)
    if existing:
        client.crons.delete(existing["cron_id"])

    client.crons.create(
        assistant_id=assistant_id,
        schedule=schedule,              # standard cron (UTC)
        input=the_input,
        name=name
    )
    print(f"Upserted cron: {name} -> {schedule} ({instrument} {timeframe})")

if __name__ == "__main__":
    # 5-minute bars
    upsert_cron("m5_eurusd", "*/5 * * * *", "EUR_USD", "M5")
    # hourly bar
    upsert_cron("h1_eurusd", "0 * * * *", "EUR_USD", "H1")
    # daily bar at 21:00 UTC (example)
    upsert_cron("d1_eurusd", "0 21 * * *", "EUR_USD", "D1")
