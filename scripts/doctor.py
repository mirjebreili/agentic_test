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
            if not assistants:
                raise ValueError(f"No assistant found for graph_id '{lg_graph_id}'")
            print(f"   ✅ Found default assistant: {assistants[0]['assistant_id']}")
        except Exception as e:
            print(f"   ❌ FAILED: Could not find default assistant: {e}")
            failures += 1

    # 3. Check LLM connectivity and capabilities
    from app.settings import settings
    from app.llm import probe_tool_calling_capability

    cfg = settings.llm
    print(f"3. Checking OpenAI-compatible LLM at {cfg.base_url} ...")
    try:
        with httpx.Client() as client:
            response = client.get(f"{cfg.base_url.replace('/v1', '')}/v1/models")
            response.raise_for_status()
            models = response.json().get("data", [])
            if any(m['id'] == cfg.model for m in models):
                print(f"   ✅ LLM is reachable and model '{cfg.model}' is available.")
            else:
                print(f"   ❌ FAILED: LLM is reachable, but model '{cfg.model}' is not found.")
                failures += 1
    except (httpx.ConnectError, httpx.HTTPStatusError) as e:
        print(f"   ❌ FAILED: Could not connect to LLM endpoint: {e}")
        failures += 1

    if failures == 0 and cfg.probe_tools:
        supports_tools = probe_tool_calling_capability()
        print(f"   - Tool Calling Probe: {'Supported ✅' if supports_tools else 'Not Supported ⚠️ (fallback may be active)'}")

    # 4. Check Tracing Configuration
    print("4. Checking Tracing/Telemetry configuration ...")
    telemetry = settings.telemetry
    print(f"   - Tracing Provider: {telemetry.tracing_provider}")
    if "langsmith" in telemetry.tracing_provider:
        if not os.environ.get("LANGSMITH_API_KEY"):
            print("   ⚠️ WARNING: LangSmith tracing is enabled, but LANGSMITH_API_KEY is not set.")
        else:
            print("   ✅ LANGSMITH_API_KEY is set.")
    if "local" in telemetry.tracing_provider:
        local_path = ROOT / telemetry.local.path
        print(f"   - Local tracing path: {local_path}")
        try:
            local_path.mkdir(parents=True, exist_ok=True)
            (local_path / ".writable_test").touch()
            (local_path / ".writable_test").unlink()
            print("   ✅ Local tracing path is writable.")
        except OSError as e:
            print(f"   ❌ FAILED: Local tracing path is not writable: {e}")
            failures += 1

    # 5. Print settings summary
    print("5. Checking active configuration ...")
    print(f"   - LLM Provider Label: {settings.llm.provider_label}")
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
