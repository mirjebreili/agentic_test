from __future__ import annotations
import os
import time
import yaml
import sys
import json
from pathlib import Path
from langgraph_sdk import get_sync_client
from langgraph_sdk.client import LangGraphClient

# --- Configuration ---
POLL_INTERVAL_SECONDS = 60
ROOT = Path(__file__).resolve().parents[1]
THREAD_MAP_FILE = ROOT / "runs" / "threads.json"

class ThreadManager:
    """Handles creation, storage, and retrieval of thread IDs with verification."""
    def __init__(self, client: LangGraphClient, file_path: Path):
        self.client = client
        self.file_path = file_path
        self._thread_map = self._load()
        self._verify_all_threads()

    def _load(self) -> dict:
        if self.file_path.exists():
            return json.loads(self.file_path.read_text())
        return {}

    def _save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.file_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self._thread_map, indent=2))
        os.replace(temp_path, self.file_path)

    def _verify_all_threads(self):
        """On startup, check if threads are stale. If so, wipe the map."""
        if not self._thread_map:
            return

        first_thread_id = next(iter(self._thread_map.values()), None)
        if not first_thread_id:
            return

        try:
            self.client.threads.get(first_thread_id)
        except Exception:
            print("Stale thread detected, assuming new server session. Wiping thread map.")
            self._thread_map = {}
            self._save()

    def ensure_thread_id(self, instrument: str, timeframe: str) -> str:
        """Get or create a thread_id, verifying its existence on the server."""
        key = f"{instrument}_{timeframe}"
        thread_id = self._thread_map.get(key)

        if thread_id:
            try:
                self.client.threads.get(thread_id)
                print(f"Reusing thread for {key}: {thread_id} (verified)")
                return thread_id
            except Exception:
                print(f"Stale thread ID for {key}: {thread_id}. Recreating...")

        return self._create_new_thread(key, instrument, timeframe)

    def force_recreate(self, instrument: str, timeframe: str) -> str:
        """Explicitly recreates a thread, bypassing any cached ID."""
        key = f"{instrument}_{timeframe}"
        return self._create_new_thread(key, instrument, timeframe)

    def _create_new_thread(self, key: str, instrument: str, timeframe: str) -> str:
        print(f"Creating new thread for {key}...")
        thread = self.client.threads.create(metadata={"instrument": instrument, "timeframe": timeframe})
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
        assistant_id = assistants[0]["assistant_id"]
        print(f"Connection successful. Using assistant {assistant_id}.")
    except Exception as e:
        print(f"Error connecting to server or finding assistant: {e}", file=sys.stderr)
        sys.exit(1)

    schedule_configs = load_schedule_config()
    if not schedule_configs:
        return

    thread_manager = ThreadManager(client, THREAD_MAP_FILE)

    try:
        while True:
            print(f"\n--- New scheduler cycle at {time.ctime()} ---")
            from app.settings import settings

            for i, config in enumerate(schedule_configs):
                if i > 0:
                    print(f"Staggering for {settings.scheduler.stagger_seconds}s...")
                    time.sleep(settings.scheduler.stagger_seconds)

                instrument = config["instrument"]
                timeframe = config["timeframe"]

                for attempt in range(2): # Allow one retry
                    try:
                        from app.settings import settings
                        thread_id = thread_manager.ensure_thread_id(instrument, timeframe)

                        run_input = {"messages": [{"role": "user", "content": f"CandleCloseEvent {instrument} {timeframe}"}]}

                        metadata = {
                            "instrument": instrument,
                            "timeframe": timeframe,
                            "mode": settings.mode,
                            "broker_provider": settings.broker_provider,
                           "llm_provider": settings.llm.provider_label,
                           "llm_model": settings.llm.model,
                            "run_reason": "scheduled",
                            "app_version": settings.app.get("version", "0.1.0"),
                        }

                        print(f"Triggering run for {instrument}/{timeframe} on thread {thread_id}...")
                        run = client.runs.create(
                            assistant_id=assistant_id,
                            thread_id=thread_id,
                            input=run_input,
                            metadata=metadata
                        )
                        print(f"Successfully triggered run {run['run_id']}.")
                        break
                    except Exception as e:
                        if "404" in str(e) and "thread" in str(e).lower() and attempt == 0:
                            print(f"Stale thread detected on run creation for {instrument}/{timeframe}. Retrying once.")
                            thread_manager.force_recreate(instrument, timeframe)
                            continue

                        print(f"Error triggering run for {instrument}/{timeframe}: {e}", file=sys.stderr)
                        break

            print(f"--- Cycle complete. Waiting for {POLL_INTERVAL_SECONDS} seconds. ---")
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nScheduler stopped by user. Exiting.")
        sys.exit(0)

if __name__ == "__main__":
    run_scheduler()
