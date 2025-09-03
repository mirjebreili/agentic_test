from __future__ import annotations
import os
import time
import yaml
import sys
import json
from pathlib import Path
from langgraph_sdk import get_sync_client

# --- Configuration ---
POLL_INTERVAL_SECONDS = 60
ROOT = Path(__file__).resolve().parents[1]
THREAD_MAP_FILE = ROOT / "runs" / "threads.json"

class ThreadManager:
    """Handles creation, storage, and retrieval of thread IDs."""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._thread_map = self._load()

    def _load(self) -> dict:
        if self.file_path.exists():
            return json.loads(self.file_path.read_text())
        return {}

    def _save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(self._thread_map, indent=2))

    def get_thread_id(self, client, instrument: str, timeframe: str) -> str:
        """Get or create a thread_id for the given instrument/timeframe pair."""
        key = f"{instrument}_{timeframe}"
        if key in self._thread_map:
            print(f"Reusing thread for {key}: {self._thread_map[key]}")
            return self._thread_map[key]

        print(f"Creating new thread for {key}...")
        thread = client.threads.create(metadata={"instrument": instrument, "timeframe": timeframe})
        thread_id = thread["thread_id"]
        self._thread_map[key] = thread_id
        self._save()
        print(f"Created thread for {key}: {thread_id}")
        return thread_id

def load_schedule_config() -> list[dict]:
    """Load the scheduler decisions from settings.yaml."""
    try:
        with open(ROOT / "config" / "settings.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config.get("scheduler", {}).get("decisions", [])
    except FileNotFoundError:
        print("Warning: config/settings.yaml not found. No schedule to run.", file=sys.stderr)
        return []

def run_scheduler():
    """Main loop to trigger graph runs on a schedule."""
    lg_url = os.environ.get("LG_URL", "http://127.0.0.1:2024")
    lg_graph_id = os.environ.get("LG_GRAPH_ID", "trader")

    print("--- Scheduler Trigger Script ---")

    try:
        client = get_sync_client(url=lg_url)
        assistants = client.assistants.search(graph_id=lg_graph_id)
        if not assistants:
            raise ValueError(f"No assistant found for graph_id '{lg_graph_id}'")
        assistant = assistants[0]
        assistant_id = assistant["assistant_id"]
        print(f"Connection successful. Using assistant {assistant_id} for graph '{lg_graph_id}'.")
    except Exception as e:
        print(f"Error connecting to server or finding assistant: {e}", file=sys.stderr)
        sys.exit(1)

    schedule_configs = load_schedule_config()
    if not schedule_configs:
        print("No trading decisions found in scheduler config. Exiting.")
        return

    print(f"Found {len(schedule_configs)} decision(s) to schedule.")
    thread_manager = ThreadManager(THREAD_MAP_FILE)

    try:
        while True:
            print(f"\n--- New scheduler cycle at {time.ctime()} ---")
            for config in schedule_configs:
                instrument = config["instrument"]
                timeframe = config["timeframe"]

                try:
                    thread_id = thread_manager.get_thread_id(client, instrument, timeframe)
                    run_input = {"messages": [{"role": "user", "content": f"CandleCloseEvent {instrument} {timeframe}"}]}

                    print(f"Triggering run for {instrument}/{timeframe} on thread {thread_id}...")
                    run = client.runs.create(assistant_id=assistant_id, thread_id=thread_id, input=run_input)
                    print(f"Successfully triggered run {run['run_id']}.")
                except Exception as e:
                    print(f"Error triggering run for {instrument}/{timeframe}: {e}", file=sys.stderr)

            print(f"--- Cycle complete. Waiting for {POLL_INTERVAL_SECONDS} seconds. ---")
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nScheduler stopped by user. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    run_scheduler()
