from __future__ import annotations
import os
from langgraph_sdk import get_sync_client

URL = os.environ.get("LG_URL", "http://127.0.0.1:2024")
GRAPH_ID = os.environ.get("LG_GRAPH_ID", "trader")  # must match langgraph.json
client = get_sync_client(url=URL)

def get_or_create_assistant(graph_id: str) -> str:
    """
    Return the default assistant_id for graph_id. Create one if missing.
    """
    try:
        # Get the default assistant for this graph id
        asst = client.assistants.get(graph_id)
        return asst["assistant_id"]
    except Exception:
        # If none exists (shouldn’t happen in dev), create one
        created = client.assistants.create(graph_id=graph_id, name=f"{graph_id}-default")
        return created["assistant_id"]

assistant_id = get_or_create_assistant(GRAPH_ID)

def upsert_cron(name: str, schedule: str, instrument: str, timeframe: str):
    run_input = {
        "messages": [
            {"role": "user", "content": f"CandleCloseEvent {instrument} {timeframe}"}
        ],
        "config": {"configurable": {"instrument": instrument, "timeframe": timeframe}}
    }

    # replace if already exists
    for c in client.crons.search():
        if c.get("name") == name:
            client.crons.delete(c["cron_id"])

    client.crons.create(
        assistant_id=assistant_id,
        schedule=schedule,  # standard cron (UTC)
        input=run_input,
        name=name,
    )
    print(f"Upserted cron: {name} -> {schedule} ({instrument} {timeframe})")

if __name__ == "__main__":
    upsert_cron("m5_eurusd", "*/5 * * * *", "EUR_USD", "M5")
    upsert_cron("h1_eurusd", "0 * * * *",   "EUR_USD", "H1")
    upsert_cron("d1_eurusd", "0 21 * * *",  "EUR_USD", "D1")
