# Multiagent Trader (LangGraph Edition)

This project implements a multi-agent FX trading system using the LangGraph framework. It is designed to be run with the LangGraph CLI, providing a powerful development and monitoring experience via the LangGraph Studio. The default configuration runs in a fully offline demo mode.

## 1. Prerequisites

- Python 3.11+
- Git

## 2. Installation

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install the project package in editable mode
pip install -e .

# 3. Install the LangGraph CLI and SDK
pip install -U "langgraph-cli[inmem]" langgraph-sdk
```

## 3. Configuration (for Demo Mode)

The project is configured to run in demo mode by default. You only need to configure your local LLM endpoint.

1.  **Create `.env` file:**
    Copy the example environment file: `cp .env.example .env`
2.  **Edit `.env`:**
    Open the `.env` file and ensure `OPENAI_BASE_URL` and `OPENAI_MODEL` point to your running local LLM server.
3.  **Confirm `settings.yaml`:**
    No changes are needed for demo mode. `config/settings.yaml` should be pre-configured to use `broker_provider: paper` and `data_provider: mock`.

## 4. Running the Application (Local Development)

The local workflow uses two terminals: one for the LangGraph server and one for a simple Python script that triggers the trading logic on a schedule.

### Terminal 1: Start the LangGraph Server

From the repository root, start the development server:

```bash
langgraph dev
```

The server will start, load the `trader` graph, and print the URL for the LangGraph Studio UI (e.g., `http://127.0.0.1:2024`). Keep this server running.

### Terminal 2: Start the Scheduler Trigger

Once the server is running, open a second terminal to start the scheduler script.

```bash
# 1. Activate the virtual environment
source .venv/bin/activate

# 2. (Optional) Set the LG_URL if your server started on a different port
# export LG_URL="http://127.0.0.1:8001"

# 3. Run the scheduler trigger
python scripts/scheduler_trigger.py
```

The script will connect to the server and begin triggering a run for each configured instrument every 60 seconds.

#### Running in the Background (Optional)
To keep the scheduler running after you close the terminal, you can use a tool like `tmux` or `screen` on macOS/Linux, or run it as a background task in Windows Task Scheduler.

## 5. LangGraph Platform Deployment (Cron Jobs)

The LangGraph cron job feature is designed for production deployments on LangGraph Platform (Plus tier). It is **not available** on the local `langgraph dev` server.

For future platform deployments, you can use the `scripts/create_crons_platform_only.py` script to register cron jobs. This script will fail gracefully if run against a local dev server.

## 6. Monitoring and Diagnostics

-   **LangGraph Studio**: Open the Studio URL from the `langgraph dev` output to see all triggered runs and inspect their traces.
-   **Paper Ledger**: The paper broker writes all simulated trades to `runs/paper_ledger.json`.
-   **Doctor Script**: Run the diagnostic `doctor.py` script to check for common issues:
    ```bash
    python scripts/doctor.py
    ```

### Stale Threads after Server Restart
The `langgraph dev` server stores all data (including threads) in memory. If you restart the server, all existing threads become invalid. The `scheduler_trigger.py` script is designed to handle this automatically by verifying threads before use and recreating them if they are stale. You should not need to do anything manually, but be aware that you will see messages about threads being recreated after a server restart.
