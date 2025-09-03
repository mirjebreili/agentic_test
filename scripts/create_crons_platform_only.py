from __future__ import annotations
import os
import sys
import httpx
from langgraph_sdk import get_sync_client

def setup_crons():
    """
    Connects to a LangGraph Platform/Plus server and creates or updates cron jobs.
    This script will not work with the local `langgraph dev` server.
    """
    lg_url = os.environ.get("LG_URL", "http://127.0.0.1:2024")
    lg_graph_id = os.environ.get("LG_GRAPH_ID", "trader")

    print(f"--- Platform Cron Setup Script ---")
    print(f"Connecting to LangGraph server at: {lg_url}")

    # --- Feature Check ---
    try:
        with httpx.Client() as http_client:
            response = http_client.get(f"{lg_url}/runs/crons/search")
            if response.status_code == 404:
                print("\nError: Cron endpoints are not available on this server.", file=sys.stderr)
                print("This script is intended for LangGraph Platform/Plus deployments.", file=sys.stderr)
                print("For local development, use `scripts/scheduler_trigger.py` instead.", file=sys.stderr)
                sys.exit(1)
            response.raise_for_status()
        client = get_sync_client(url=lg_url)
        print("Successfully connected and cron endpoints are available.")
    except (httpx.ConnectError, httpx.HTTPStatusError) as e:
        print(f"Error connecting to server: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Get Assistant ID ---
    print(f"Searching for assistant for graph '{lg_graph_id}'...")
    try:
        assistants = client.assistants.search(graph_id=lg_graph_id)
        if not assistants:
            print(f"No default assistant found for graph '{lg_graph_id}'. Creating one.")
            asst = client.assistants.create(graph_id=lg_graph_id, name=f"{lg_graph_id}-default")
        else:
            asst = assistants[0]

        assistant_id = asst["assistant_id"]
        print(f"Using Assistant ID: {assistant_id}")
    except Exception as e:
        print(f"Error finding or creating assistant: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Upsert Crons ---
    def upsert_cron(name: str, schedule: str, instrument: str, timeframe: str):
        run_input = {
            "messages": [{"role": "user", "content": f"CandleCloseEvent {instrument} {timeframe}"}]
        }
        for c in client.crons.search(assistant_id=assistant_id):
            if c.get("name") == name:
                client.crons.delete(c["cron_id"])
        client.crons.create(assistant_id=assistant_id, schedule=schedule, input=run_input, name=name)
        print(f"Upserted cron: {name} -> {schedule} ({instrument} {timeframe})")

    print("Upserting cron jobs...")
    upsert_cron("m5_eurusd", "*/5 * * * *", "EUR_USD", "M5")
    upsert_cron("h1_eurusd", "0 * * * *",   "EUR_USD", "H1")
    upsert_cron("d1_eurusd", "0 21 * * *",  "EUR_USD", "D1")
    print("--- Cron setup complete. ---")

if __name__ == "__main__":
    setup_crons()
