from __future__ import annotations
import os
import sys
import json
from pathlib import Path
import httpx
from langgraph_sdk import get_sync_client

ROOT = Path(__file__).resolve().parents[1]
THREAD_MAP_FILE = ROOT / "runs" / "threads.json"

def run_diagnostics():
    """
    Runs a series of checks to diagnose common configuration and connectivity issues.
    """
    failures = 0
    lg_client = None

    # 1. Check LangGraph Server connectivity
    lg_url = os.environ.get("LG_URL", "http://127.0.0.1:2024")
    print(f"1. Checking LangGraph Server at {lg_url} ...")
    try:
        with httpx.Client() as client:
            response = client.get(f"{lg_url}/ok")
            response.raise_for_status()
        print("   ✅ Server is reachable.")
        lg_client = get_sync_client(url=lg_url)
    except (httpx.ConnectError, httpx.HTTPStatusError) as e:
        print(f"   ❌ FAILED: Could not connect to LangGraph Server: {e}")
        failures += 1

    # 2. Verify default assistant exists
    lg_graph_id = os.environ.get("LG_GRAPH_ID", "trader")
    print(f"2. Checking for assistant for graph '{lg_graph_id}' ...")
    if lg_client:
        try:
            assistants = lg_client.assistants.search(graph_id=lg_graph_id)
            if assistants:
                print(f"   ✅ Found default assistant: {assistants[0]['assistant_id']}")
            else:
                raise ValueError(f"No assistant found for graph_id '{lg_graph_id}'")
        except Exception as e:
            print(f"   ❌ FAILED: Could not find default assistant: {e}")
            failures += 1

    # 3. Check Thread Mapping
    print("3. Checking thread mapping file...")
    if lg_client and THREAD_MAP_FILE.exists():
        thread_map = json.loads(THREAD_MAP_FILE.read_text())
        stale_threads = 0
        for key, thread_id in thread_map.items():
            try:
                lg_client.threads.get(thread_id)
            except Exception:
                stale_threads += 1
        if stale_threads > 0:
            print(f"   ⚠️ Found {stale_threads} stale thread(s). They will be auto-recreated.")
        else:
            print(f"   ✅ All {len(thread_map)} threads in mapping are valid.")

    # 4. Check LLM connectivity
    from app.settings import settings
    provider = settings.llm.provider.lower()
    print(f"4. Checking LLM Provider '{provider}' ...")

    if provider == "vllm":
        cfg = settings.llm.vllm
        print(f"   - Checking VLLM at {cfg.base_url} for model {cfg.model} ...")
        try:
            with httpx.Client() as client:
                response = client.get(f"{cfg.base_url.replace('/v1', '')}/v1/models")
                response.raise_for_status()
            print("     ✅ VLLM endpoint is reachable.")
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"     ❌ FAILED: Could not connect to VLLM: {e}")
            failures += 1
    elif provider == "ollama":
        cfg = settings.llm.ollama
        print(f"   - Checking Ollama at {cfg.base_url} for model {cfg.model} ...")
        try:
            with httpx.Client() as client:
                response = client.get(f"{cfg.base_url}/api/tags")
                response.raise_for_status()
                models = response.json().get("models", [])
                if any(m['name'] == cfg.model for m in models):
                    print(f"     ✅ Ollama is reachable and model '{cfg.model}' is available.")
                else:
                    print(f"     ❌ FAILED: Ollama is reachable, but model '{cfg.model}' is not found.")
                    print(f"        (Hint: Run `ollama pull {cfg.model}`)")
                    failures += 1
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"     ❌ FAILED: Could not connect to Ollama: {e}")
            failures += 1

    # 5. Print settings summary
    print("5. Checking active configuration ...")
    print(f"   - Mode: {settings.mode}")
    print(f"   - Broker Provider: {settings.broker_provider}")
    print(f"   - Data Provider: {settings.data_provider}")

    # Final result
    print("-" * 20)
    if failures > 0:
        print(f"🔴 Found {failures} critical issue(s).")
        sys.exit(1)
    else:
        print("🟢 All checks passed.")

if __name__ == "__main__":
    run_diagnostics()
