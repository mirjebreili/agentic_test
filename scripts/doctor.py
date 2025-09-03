from __future__ import annotations
import os
import sys
import httpx
from langgraph_sdk import get_sync_client

def run_diagnostics():
    """
    Runs a series of checks to diagnose common configuration and connectivity issues.
    """
    failures = 0

    # 1. Check LangGraph Server connectivity
    lg_url = os.environ.get("LG_URL", "http://127.0.0.1:2024")
    print(f"1. Checking LangGraph Server at {lg_url} ...")
    try:
        with httpx.Client() as client:
            response = client.get(f"{lg_url}/ok")
            response.raise_for_status()
        print("   ✅ Server is reachable.")
    except (httpx.ConnectError, httpx.HTTPStatusError) as e:
        print(f"   ❌ FAILED: Could not connect to LangGraph Server: {e}")
        failures += 1

    # 2. Verify default assistant exists
    lg_graph_id = os.environ.get("LG_GRAPH_ID", "trader")
    print(f"2. Checking for assistant for graph '{lg_graph_id}' ...")
    if failures == 0: # Skip if server is down
        try:
            lg_client = get_sync_client(url=lg_url)
            assistants = lg_client.assistants.search(graph_id=lg_graph_id)
            if assistants:
                print(f"   ✅ Found default assistant: {assistants[0]['assistant_id']}")
            else:
                raise ValueError(f"No assistant found for graph_id '{lg_graph_id}'")
        except Exception as e:
            print(f"   ❌ FAILED: Could not find default assistant: {e}")
            print("      (Hint: Make sure the server has loaded the graph from langgraph.json)")
            failures += 1

    # 3. Check for Cron endpoint availability
    print("3. Checking for Cron Job API availability ...")
    if failures == 0:
        try:
            with httpx.Client() as client:
                # This is an arbitrary cron endpoint to check for 404
                response = client.get(f"{lg_url}/runs/crons/search")
                if response.status_code == 404:
                     print("   ✅ Cron endpoints not available on local dev server (as expected).")
                else:
                    response.raise_for_status()
                    print("   ✅ Cron endpoints are available (Platform/Plus server detected).")
        except httpx.HTTPStatusError as e:
            print(f"   ⚠️ WARNING: Unexpected status when checking cron endpoints: {e}")

    # 4. Check LLM connectivity
    from app.settings import settings
    llm_url = settings.llm.base_url
    print(f"4. Checking LLM at {llm_url} ...")
    if llm_url and llm_url.startswith("http"):
        try:
            with httpx.Client() as client:
                response = client.get(f"{llm_url.replace('/v1', '')}/v1/models")
                response.raise_for_status()
            print("   ✅ LLM endpoint is reachable.")
        except (httpx.ConnectError, httpx.HTTPStatusError) as e:
            print(f"   ⚠️ WARNING: Could not connect to LLM: {e}")
    else:
        print("   ⚠️ WARNING: LLM base URL is not a valid http endpoint.")

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
