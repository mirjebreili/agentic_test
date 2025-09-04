from __future__ import annotations
import os
import sys
import json
import glob
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

    # 3. Graph Dry-Run
    print("3. Performing graph dry-run ...")
    if lg_client and "assistants" in locals():
        try:
            # A minimal input that won't trigger tools
            dry_run_input = {"messages": [{"role": "user", "content": "DryRunEvent"}]}
            thread = lg_client.threads.create(metadata={"source": "doctor_dry_run"})
            run = lg_client.runs.create(
                assistant_id=assistants[0]["assistant_id"],
                thread_id=thread["thread_id"],
                input=dry_run_input,
            )
            print(f"   ✅ Graph dry-run successful. Run ID: {run['run_id']}")
        except Exception as e:
            print(f"   ❌ FAILED: Graph dry-run failed: {type(e).__name__}: {e}")
            failures += 1
    elif not lg_client:
        print("   ⚪️ SKIPPED: LangGraph client not available.")

    # 4. Check LLM connectivity and capabilities
    from app.settings import settings
    from app.llm import probe_tool_calling_capability, make_llm
    from langchain_core.messages import HumanMessage
    import time

    cfg = settings.llm
    print(f"4. Checking OpenAI-compatible LLM at {cfg.base_url} ...")
    try:
        with httpx.Client() as client:
            base_url = cfg.base_url.removesuffix("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            response = client.get(f"{base_url}/models")
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

    # 3b. LLM Generation Smoke Test
    print(f"   - Performing generation smoke test with model '{cfg.model}'...")
    try:
        start_time = time.monotonic()
        llm = make_llm()
        response = llm.invoke([HumanMessage(content="Hello!")], config={"max_tokens": 5})
        latency_ms = (time.monotonic() - start_time) * 1000

        if response.content:
            print(f"   ✅ Generation successful (latency: {latency_ms:.0f}ms). Response: '{response.content[:50]}...'")
        else:
            print("   ❌ FAILED: Generation produced an empty response.")
            failures += 1
    except Exception as e:
        print(f"   ❌ FAILED: Generation smoke test failed: {type(e).__name__}: {e}")
        failures += 1


    # 5. Check Tracing Configuration
    print("5. Checking Tracing/Telemetry configuration ...")
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

    # 6. Print settings summary
    print("6. Checking active configuration ...")
    print(f"   - LLM Provider Label: {settings.llm.provider_label}")
    print(f"   - Mode: {settings.mode}")
    print(f"   - Broker Provider: {settings.broker_provider}")
    print(f"   - Data Provider: {settings.data.provider}")

    # 7. Recent Decisions Summary
    check_recent_decisions()

    # 8. External Provider Checks
    print("8. Checking External Providers...")
    failures += check_parquet_engine()
    failures += check_data_provider()
    failures += check_broker_provider()

    # Final result
    print("-" * 20)
    if failures > 0:
        print(f"🔴 Found {failures} critical issue(s).")
        sys.exit(1)
    else:
        print("🟢 All checks passed.")

def check_recent_decisions(max_runs: int = 10):
    """Reads local logs and prints a summary of the last few decisions."""
    from app.settings import settings
    print("7. Checking recent decisions from local logs ...")

    log_dir = ROOT / settings.telemetry.local.path
    list_of_files = glob.glob(str(log_dir / "*.jsonl"))
    if not list_of_files:
        print("   ⚪️ No local log files found.")
        return

    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"   - Reading from: {Path(latest_file).name}")

    with open(latest_file, "r") as f:
        lines = f.readlines()

    runs = {}
    for line in lines[-200:]: # Read more lines to be safe
        try:
            log = json.loads(line)
            run_id = log.get("run_id")
            if not run_id: continue

            if run_id not in runs:
                runs[run_id] = {"run_id": run_id, "nodes": {}}

            # Update run metadata from the first log entry that has it
            if "decision_key" not in runs[run_id] and log.get("decision_key"):
                runs[run_id].update({
                    "decision_key": log.get("decision_key"),
                    "ts": log.get("ts_iso"),
                    "instrument": log.get("instrument"),
                    "timeframe": log.get("timeframe"),
                })

            node_name = log.get("node")
            if not node_name: continue

            if node_name == "strategy" and log.get("event_type") == "node_enter":
                runs[run_id]["prompt_id"] = log.get("prompt_id")
                runs[run_id]["prompt_version"] = log.get("prompt_version")

            if log.get("event_type") == "node_exit":
                if log.get("status") == "error":
                    runs[run_id]["nodes"][node_name] = f"ERROR: {log.get('error_type')}"
                elif "output" in log and isinstance(log["output"], dict):
                    # Extract structured output if available
                    output_messages = log["output"].get("messages", [])
                    if output_messages and isinstance(output_messages[-1], dict):
                         content = output_messages[-1].get("content", "")
                         runs[run_id]["nodes"][node_name] = content
        except json.JSONDecodeError:
            continue

    # Filter to latest run per decision key
    latest_runs = {}
    for run in sorted(runs.values(), key=lambda r: r.get("ts", ""), reverse=True):
        key = run.get("decision_key")
        if key and key not in latest_runs:
            latest_runs[key] = run

    if not latest_runs:
        print("   ⚪️ No decision runs found in recent logs.")
        return

    print("   ---")
    for key, run in sorted(latest_runs.items())[:max_runs]:
        prompt_info = f"(prompt: {run.get('prompt_id')} v{run.get('prompt_version')})"
        print(f"   - Decision: {key} (Run: {run['run_id'][:8]} at {run.get('ts')}) {prompt_info}")
        strategy_out = run["nodes"].get("strategy", "N/A")
        signal_out = run["nodes"].get("signal", "N/A")
        risk_out = run["nodes"].get("risk", "N/A")
        exec_out = run["nodes"].get("exec", "N/A")

        print(f"     - Strategy: {strategy_out}")
        print(f"     - Signal:   {signal_out}")
        print(f"     - Risk:     {risk_out}")
        print(f"     - Exec:     {exec_out}")
    print("   ---")

def check_data_provider() -> int:
    """Checks the active data provider."""
    import asyncio
    from app.settings import settings
    from app.tools.standard import get_candles
    from app.tools.data_models import FeatureSummary
    from app.tools.errors import ProviderError

    failures = 0
    provider = settings.data.provider
    print(f"   - Data Provider: {provider}")

    if provider == "mock":
        try:
            summary_json = asyncio.run(get_candles.ainvoke({"instrument": "EUR_USD", "timeframe": "M5", "count": 3}))
            summary = FeatureSummary.model_validate_json(summary_json)
            if len(summary.last_n_closes) == 3:
                 print(f"   ✅ Mock provider returned a valid FeatureSummary.")
            else:
                print(f"   ❌ FAILED: Mock provider returned an invalid summary: {summary}")
                failures += 1
        except ProviderError as e:
            print(f"   ❌ FAILED: Mock provider check failed: {e}")
            failures += 1
        except Exception as e:
            print(f"   ❌ FAILED: Mock provider check failed unexpectedly: {type(e).__name__}: {e}")
            failures += 1

    # TODO: Add checks for real data providers here

    return failures

def check_broker_provider() -> int:
    """Checks the active broker provider."""
    from app.settings import settings
    failures = 0
    provider = settings.broker_provider
    print(f"   - Broker Provider: {provider}")

    if provider == "paper":
        try:
            # Check if the paper ledger path is writable
            ledger_path = ROOT / settings.paper.get("ledger_path", "runs/paper_ledger.json")
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            (ledger_path.parent / ".writable_test").touch()
            (ledger_path.parent / ".writable_test").unlink()
            print(f"   ✅ Paper broker ledger path is writable: {ledger_path}")
        except OSError as e:
            print(f"   ❌ FAILED: Paper broker ledger path is not writable: {e}")
            failures += 1

    elif provider == "oanda":
        if not settings.oanda.api_key or not settings.oanda.account_id:
            print("   ⚪️ OANDA provider is selected, but API key or account ID is missing.")
            return failures

        try:
            headers = {"Authorization": f"Bearer {settings.oanda.api_key}"}
            url = f"{settings.oanda.base}/v3/accounts/{settings.oanda.account_id}/summary"
            with httpx.Client(timeout=10) as client:
                r = client.get(url, headers=headers)
                r.raise_for_status()
                acc_summary = r.json().get("account", {})
                print(f"   ✅ OANDA connection successful. Account: {acc_summary.get('alias', 'N/A')}, Currency: {acc_summary.get('currency')}")
        except httpx.HTTPStatusError as e:
            print(f"   ❌ FAILED: OANDA API request failed: {e.response.status_code} {e.response.text}")
            failures += 1
        except Exception as e:
            print(f"   ❌ FAILED: OANDA connection failed: {type(e).__name__}: {e}")
            failures += 1

    return failures

def check_parquet_engine() -> int:
    """Checks for a valid Parquet engine if format is 'parquet'."""
    from app.settings import settings
    if settings.data.cache_format == "parquet":
        try:
            import pyarrow
            print("   ✅ Parquet engine 'pyarrow' is available.")
            return 0
        except ImportError:
            pass
        try:
            import fastparquet
            print("   ✅ Parquet engine 'fastparquet' is available.")
            return 0
        except ImportError:
            print("   ❌ FAILED: `data.cache_format` is 'parquet' but no engine found.")
            print("             Please `pip install pyarrow` (recommended) or `fastparquet`.")
            return 1
    return 0

if __name__ == "__main__":
    run_diagnostics()
