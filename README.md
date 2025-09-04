# Multiagent Trader (LangGraph Edition)

This project implements a multi-agent FX trading system using the LangGraph framework. It is designed to be run with the LangGraph CLI, providing a powerful development and monitoring experience via the LangGraph Studio.

## Key Architectural Features
- **Unified LLM Interface**: Uses a single OpenAI-compatible client to connect to various LLM backends like VLLM or Ollama.
- **Professional Prompt Management**: All agent prompts are externalized into versioned Markdown files under `app/prompts/`, making them easy to manage, test, and override.
- **Local-First Scheduling**: Uses a simple, robust Python script to trigger graph runs, avoiding dependencies on platform-specific features for local development.
- **Comprehensive Tracing**: Includes a built-in telemetry system that logs detailed traces to local CSV/JSONL files for auditing and debugging.
- **Robust Error Handling**: The application is designed to be resilient, with features like scheduler staggering, LLM call retries, and detailed error logging.

## 1. Setup & Environment

### Create a virtualenv and install
```bash
# 1. Create and activate a virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -e .
pip install -U "langgraph-cli[inmem]" langgraph-sdk
```

### Create `.env` from template
```bash
cp .env.example .env
```
The `.env` file is used to configure the application's connection to the LLM backend and other services. Here are the key variables:

- `OPENAI_BASE_URL`: The full URL to the OpenAI-compatible endpoint, including the `/v1` path.
- `OPENAI_MODEL`: The name of the model to use for generation.
- `LLM_PROVIDER` (Optional): A label for the LLM provider (e.g., `OLLAMA`, `VLLM`). If not set, it will be inferred from the `OPENAI_BASE_URL`.
- `MODE`: The application's operating mode. The default is `paper` for a simulated trading environment with mock data.
- `OANDA_API_KEY`, `OANDA_ACCOUNT_ID`: Your OANDA API credentials (only needed for live or practice modes).

### Choose your LLM backend (exact, copy-paste)
The application uses a single OpenAI-compatible client. You must provide the full base URL, including the `/v1` path.

**vLLM Example**
```dotenv
OPENAI_BASE_URL=http://localhost:8000/v1
OPENAI_MODEL=Your-VLLM-Model-Name
# OPENAI_API_KEY can be anything non-empty if your server requires it
```

**Ollama Example**
```dotenv
# First, start the Ollama daemon separately and pull a tool-capable model:
#   ollama pull llama3.1:8b-instruct
OPENAI_BASE_URL=http://127.0.0.1:11434/v1
OPENAI_MODEL=llama3.1:8b-instruct
# OPENAI_API_KEY can be any non-empty value for Ollama
OPENAI_API_KEY=ollama
```
**Tip:** The application will print the resolved LLM endpoint and model on startup so you can verify what it will hit.

## 2. Running Locally (Two Terminals)

The local workflow uses two terminals: one for the LangGraph server and one for the scheduler script.

### Terminal 1 — LangGraph dev server
```bash
langgraph dev
```
- **Notes**: This starts an in-memory LangGraph server. All threads and runs will vanish on restarts. The LangGraph Studio URL should open automatically in your browser.

### Terminal 2 — Scheduler trigger
```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the scheduler trigger
python scripts/scheduler_trigger.py
```
- **What it does**: This script looks up the “trader” assistant, verifies or creates one thread per decision (e.g., `EUR_USD_M5`), and triggers a run for each on a configurable interval. The triggers are staggered to avoid overwhelming local LLM servers.
- **Where to look**: It prints run IDs to the console. Detailed per-node telemetry goes to `runs/traces/`.

## 3. Doctor: How to Use It to Debug
The `doctor.py` script runs a series of checks to diagnose common configuration and connectivity issues.

**Run doctor**
```bash
python scripts/doctor.py
```
It prints a checklist. Here is what each section means and what to do if it fails:

-   **LangGraph server**: Checks for server reachability and the presence of the "trader" assistant.
    -   **If failing**: Verify that `langgraph dev` is running, `langgraph.json` points to `app/lg_entry.py:make_graph`, and you are on the correct port.
-   **Dry-run**: Creates a temporary thread and posts a minimal “DryRunEvent” run.
    -   **If failing**: The server cannot execute a real run. Check for graph import errors or issues with node initialization.
-   **LLM generation smoke**: Performs a 1–2 token chat completion.
    -   **If failing**: The LLM is not able to generate a response. Confirm that the model is pulled (Ollama) or served (vLLM), the `OPENAI_BASE_URL` is correct, and timeouts are not too low.
-   **Recent Decisions**: Tails the JSONL logs and shows the last outcomes per decision key.
    -   **If failing**: If fields are missing, tracing may be misconfigured or the run may have crashed early.

## 4. Reading the Logs (CSV & JSONL)
**Where:** `runs/traces/YYYY-MM-DD_actions.csv|jsonl`

**Key columns/fields**
-   `ts_iso`: Event time (UTC).
-   `event_type`: The type of event, e.g., `node_enter`, `node_exit`, `tool_call`, `error`.
-   `node`: The name of the graph node where the event occurred.
-   `decision_key`: A unique identifier for the trading decision, e.g., `EUR_USD_M5`.
-   `run_id`, `thread_id`: LangGraph identifiers for the run and thread.
-   `llm_provider`, `llm_model`: The LLM provider label and model name.
-   `features_digest`, `cache_path`: The hash of the features used for the decision and the path to the full candle data.
-   `status`: `ok` or `error`.
-   `error_type`, `error_message`: Detailed error information, including endpoint, model, attempt, and timeout for LLM errors.
-   `latency_ms`: The latency of the node or tool call in milliseconds.

**How to interpret**
-   **Happy path example**: Expect to see `node_enter,strategy` → `node_exit,strategy,status=ok` with a `preset` and `rationale`, followed by `signal`, `risk`, and `exec` nodes.
-   **LLM issues**: Look for `error_type` like `ConnectTimeout`. Check `base_url`, `model`, `attempt`, and `timeout`. Consider adjusting timeouts or the scheduler stagger in `config/settings.yaml`.
-   **Thread issues**: If you see a 404 error on a thread run, the dev server likely restarted and the in-memory threads were lost. The scheduler will automatically recreate the threads on the next cycle.

## 5. Graph API & Execution Flow
The scheduler client communicates with the LangGraph server by creating runs on threads.

-   **Threads**: One thread is created for each decision key (e.g., `EUR_USD_M5`).
-   **Runs**: A run is created on a thread with an input message like `"CandleCloseEvent EUR_USD M5"` and a configuration dictionary containing metadata for the run.

**Graph State & Nodes**
The graph operates on a state dictionary that is passed between nodes. Key fields include: `instrument`, `timeframe`, `messages`.

**Nodes**
1.  **strategy**:
    -   Calls the `get_candles` tool, which returns a compact `FeatureSummary`.
    -   The LLM uses this summary to choose a strategy `preset` and `rationale`.
    -   **Conditional edge**: May end the run early if the market is deemed "no-trade".
2.  **signal**:
    -   An LLM or a deterministic rule transforms the strategy preset and features into a trading `action` (buy/sell/hold).
    -   **Conditional edge**: May end the run on a "hold" signal.
3.  **risk**:
    -   Computes `stop_loss` and `take_profit` levels based on volatility (ATR).
    -   Can veto a trade based on risk parameters.
    -   **Conditional edge**: A veto will end the run.
4.  **exec** (paper):
    -   Builds a paper order intent. No real trading occurs.
    -   The run ends here.

## 6. Prompts
-   **Location & naming**: `app/prompts/<agent>/<name>__v<ver>.md` with YAML front-matter.
-   **Validation**: The application will raise an error on startup if any prompt is missing required metadata fields (`id`, `version`, `role`, etc.).
-   **Overrides**: `app/prompts_overrides/<env>/...` for environment-specific changes.
-   **Trace**: Each node logs `prompt_id` and `prompt_version` so runs are auditable by prompt version.

## 7. Troubleshooting
-   **LangGraph can’t find assistant**: Ensure `langgraph.json` maps `"trader": "app/lg_entry.py:make_graph"` and the server is running.
-   **404 on thread run**: The dev server restarted; threads are in-memory. The scheduler will recreate threads automatically.
-   **LLM generation fails**: Ensure the model is pulled (Ollama) or served (vLLM), confirm the `OPENAI_BASE_URL` is correct, and consider increasing timeouts or the scheduler stagger in `config/settings.yaml`.
-   **Logs empty/missing fields**: Verify your telemetry configuration in `config/settings.yaml`. Check that the `strategy` node is correctly outputting the `features_digest` and `cache_path`.
