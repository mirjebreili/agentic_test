# Multiagent Trader (LangGraph Edition)

This project implements a multi-agent FX trading system using the LangGraph framework. It is designed to be run with the LangGraph CLI, providing a powerful development and monitoring experience via the LangGraph Studio.

The default configuration runs in a fully offline demo mode using a paper broker and mock data, so no API keys are required to get started.

## 1. Prerequisites

- Python 3.11+
- Git

## 2. Installation

First, clone the repository and set up the Python virtual environment.

```bash
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

## 4. Running the Application

The application uses a two-process model for development: the LangGraph server runs the graph, and a separate scheduler script triggers the graph on a timer.

### Terminal 1: Start the LangGraph Server

Start the dev server from the repository root. This will serve the graph and the Studio UI.

```bash
langgraph dev
```

The server will start and print the URL for the LangGraph Studio (e.g., `http://127.0.0.1:2024`). Keep this server running.

### Terminal 2: Start the Scheduler Trigger

Once the server is running, open a second terminal to start the scheduler script. This script will periodically trigger the trading logic.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Set the environment variables for the script
export LG_URL="http://127.0.0.1:2024"  # Use the exact URL from the server output
export LG_GRAPH_ID="trader"           # Must match the graph ID in langgraph.json

# Run the scheduler trigger
python scripts/scheduler_trigger.py
```

The script will now trigger a new run of the `trader` graph every 60 seconds (by default).

## 5. Monitoring

-   **LangGraph Studio**: Open the Studio URL from the `langgraph dev` output in your browser. You can see all triggered runs, inspect their traces, and view the state at each step.
-   **Paper Ledger**: The paper broker writes all simulated trades to `runs/paper_ledger.json`. You can inspect this file to see your positions and PnL.

## 6. Troubleshooting

Run the diagnostic "doctor" script to check for common issues.

```bash
# Set the same env vars as for the scheduler trigger
export LG_URL="http://127.0.0.1:2024"
export LG_GRAPH_ID="trader"
python scripts/doctor.py
```
This will check for server connectivity, assistant existence, and LLM reachability.
