from __future__ import annotations
import os
import time
import yaml
from pathlib import Path
from langgraph_sdk import get_sync_client

# --- Configuration ---
POLL_INTERVAL_SECONDS = 60
ROOT = Path(__file__).resolve().parents[1]

def load_schedule_config() -> list[dict]:
    """Load the scheduler decisions from settings.yaml."""
    try:
        with open(ROOT / "config" / "settings.yaml", "r") as f:
            # We don't need to expand env vars for this part of the config
            config = yaml.safe_load(f)
        return config.get("scheduler", {}).get("decisions", [])
    except FileNotFoundError:
        print("Warning: config/settings.yaml not found. No schedule to run.")
        return []

def run_scheduler():
    """
    Main loop to trigger graph runs on a schedule.
    """
    lg_url = os.environ.get("LG_URL", "http://127.0.0.1:2024")
    lg_graph_id = os.environ.get("LG_GRAPH_ID", "trader")

    print("--- Scheduler Trigger Script ---")
    print(f"Connecting to LangGraph server at: {lg_url}")
    print(f"Target graph ID: {lg_graph_id}")

    try:
        client = get_sync_client(url=lg_url)
        # Quick check to see if the server is up
        client.assistants.get(lg_graph_id)
        print("Connection successful and assistant found.")
    except Exception as e:
        print(f"Error connecting to server or finding assistant: {e}")
        print("Please ensure the LangGraph server is running with the 'trader' graph loaded.")
        return

    schedule_configs = load_schedule_config()
    if not schedule_configs:
        print("No trading decisions found in scheduler config. Exiting.")
        return

    print(f"Found {len(schedule_configs)} decision(s) to schedule.")

    while True:
        print(f"\n--- New scheduler cycle at {time.ctime()} ---")
        for config in schedule_configs:
            instrument = config["instrument"]
            timeframe = config["timeframe"]

            print(f"Triggering graph for {instrument} {timeframe}...")

            run_input = {
                "messages": [
                    {"role": "user", "content": f"CandleCloseEvent {instrument} {timeframe}"}
                ]
            }

            try:
                # Invoke the graph on the server
                # We don't need the result here, just to trigger it
                client.runs.create(
                    assistant_id=lg_graph_id,
                    input=run_input,
                )
                print(f"Successfully triggered run for {instrument} {timeframe}.")
            except Exception as e:
                print(f"Error triggering run for {instrument} {timeframe}: {e}")

        print(f"--- Cycle complete. Waiting for {POLL_INTERVAL_SECONDS} seconds. ---")
        time.sleep(POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    run_scheduler()
