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
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  **Edit `.env`:**
    Open the `.env` file and ensure `OPENAI_BASE_URL` and `OPENAI_MODEL` point to your running local LLM server.
    ```dotenv
    # .env
    MODE=PAPER
    OPENAI_BASE_URL=http://localhost:8000/v1
    OPENAI_MODEL=Qwen/Qwen2.5-7B-Instruct
    ```
3.  **Confirm `settings.yaml`:**
    No changes are needed for demo mode. `config/settings.yaml` should be pre-configured to use `broker_provider: paper` and `data_provider: mock`.

## 4. Running the Application

The application runs using the LangGraph CLI server and a separate script to create scheduled jobs.

### Terminal 1: Start the LangGraph Server

From the repository root, start the development server:

```bash
langgraph dev --config ./langgraph.json
```

The server will start, load the `trader` graph, and print the URL for the LangGraph Studio UI (e.g., `http://127.0.0.1:2024`). Keep this server running.

### Terminal 2: Register Cron Jobs

Once the server is running, open a second terminal to register the scheduled trading jobs.

```bash
# 1. Activate the virtual environment
source .venv/bin/activate

# 2. Set environment variables for the script
export LG_URL="http://127.0.0.1:2024"  # Use the exact URL from the server output
export LG_GRAPH_ID="trader"           # Must match the graph ID in langgraph.json

# 3. Run the cron script
python scripts/create_crons.py
```

The script will connect to the server and print a confirmation for each cron job created.

## 5. Monitoring

-   **LangGraph Studio**: Open the Studio URL from the `langgraph dev` output to see all triggered runs, inspect their traces, and view the state at each step.
-   **Paper Ledger**: The paper broker writes all simulated trades to `runs/paper_ledger.json`.

## 6. Troubleshooting

Run the diagnostic "doctor" script to check for common issues:

```bash
# Set the same env vars as for the cron script
export LG_URL="http://127.0.0.1:2024"
export LG_GRAPH_ID="trader"
python scripts/doctor.py
```

-   **Connection Errors**: If the `create_crons.py` or `doctor.py` scripts fail to connect, ensure the `langgraph dev` server is running and your `LG_URL` variable exactly matches the server's address.
-   **Graph Not Found**: If the server logs show the graph didn't load, check the `graphs` path in `langgraph.json` and ensure `app/__init__.py` exists.
-   **LLM Calls Fail**: Verify your local LLM server is running and `OPENAI_BASE_URL` in `.env` is correct.
