# Multiagent Trader (LangGraph Edition)

This project implements a multi-agent FX trading system using the LangGraph framework. It runs as a native LangGraph CLI application, with trading decisions triggered by cron jobs. The default configuration runs in a fully offline demo mode using a paper broker and mock data, so no API keys are required to get started.

## 1. Prerequisites

- Python 3.11+
- Git

## 2. Installation

First, clone the repository and set up the Python virtual environment.

```bash
# Clone the repository (if you haven't already)
# git clone <repo_url>
# cd multiagent-trader

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the project package in editable mode
pip install -e .

# Install the LangGraph CLI and SDK
pip install -U "langgraph-cli[inmem]" langgraph-sdk
```

## 3. Configuration (for Demo Mode)

The project is configured to run in a demo mode by default. You just need to set up your local LLM endpoint.

1.  **Copy the environment file:**
    ```bash
    cp .env.example .env
    ```
2.  **Edit `.env`:**
    Open the `.env` file and ensure `OPENAI_BASE_URL` and `OPENAI_MODEL` are set correctly for your local LLM server.
    ```dotenv
    MODE=PAPER
    OPENAI_BASE_URL=http://localhost:8000/v1
    OPENAI_MODEL=Qwen/Qwen2.5-7B-Instruct
    ```
3.  **Confirm `settings.yaml`:**
    No changes are needed for the demo mode. `config/settings.yaml` should be pre-configured to use the paper broker and mock data provider (`broker_provider: paper`, `data_provider: mock`).

## 4. Running the Application

The application now runs as a LangGraph server. You will need two terminals.

### Terminal 1: Start the LangGraph Server

Start the dev server from the repository root. It will hot-reload on code changes.

```bash
langgraph dev
```

The server will start and print the URL for the LangGraph Studio UI (e.g., `http://127.0.0.1:2024`). Keep this server running.

### Terminal 2: Register Cron Jobs

Once the server is running, open a second terminal to register the scheduled trading jobs.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Set the environment variables for the script
export LG_URL="http://127.0.0.1:2024"  # Use the exact URL from the server output
export LG_GRAPH_ID="trader"           # Must match the graph ID in langgraph.json

# Run the cron script
python scripts/create_crons.py
```

You should see output confirming that the cron jobs were created:
```
Upserted cron: m5_eurusd -> */5 * * * * (EUR_USD M5)
Upserted cron: h1_eurusd -> 0 * * * * (EUR_USD H1)
Upserted cron: d1_eurusd -> 0 21 * * * (EUR_USD D1)
```

## 5. Monitoring

-   **LangGraph Studio**: Open the Studio URL from the `langgraph dev` output in your browser. You can see all triggered runs, inspect their traces, and view the state at each step.
-   **Paper Ledger**: The paper broker writes all simulated trades to `runs/paper_ledger.json`. You can inspect this file to see your positions and PnL.

## 6. Troubleshooting

-   **Cron script can't connect**:
    -   Ensure the `langgraph dev` server is running.
    -   Verify that the `LG_URL` environment variable exactly matches the URL and port printed by the server.
-   **Graph not found on server start**:
    -   Make sure you are running `langgraph dev` from the repository root where `langgraph.json` is located.
    -   Check that `langgraph.json` has the correct path to `app/lg_entry.py`.
    -   Ensure `app/__init__.py` exists.
-   **LLM calls fail**:
    -   Verify your local LLM server is running.
    -   Check that `OPENAI_BASE_URL` in your `.env` file is correct and reachable.
-   **Run the Doctor Script**:
    For a quick diagnostic check, run the `doctor.py` script:
    ```bash
    # Set the same env vars as for the cron script
    export LG_URL="http://127.0.0.1:2024"
    export LG_GRAPH_ID="trader"
    python scripts/doctor.py
    ```
