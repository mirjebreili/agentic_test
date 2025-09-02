# Multiagent Trader (LangGraph + vLLM)

This project implements a multi-agent FX trading system using LangGraph, a local LLM (via vLLM), and a configurable set of data and brokerage providers.

## 1) Installation

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the project and its dependencies
pip install -e .

# Install LangGraph CLI and SDK
pip install -U "langgraph-cli[inmem]" langgraph-sdk
```

## 2) Start Local LLM Server

In a separate terminal, start your vLLM server (or any OpenAI-compatible API server).

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000
```

## 3) Configuration

*   Copy `.env.example` to `.env` and set `OPENAI_BASE_URL` to point to your running LLM server.
*   The default `config/settings.yaml` is configured to run in a fully offline demo mode using a paper broker and mock data provider. No API keys are needed to get started.

## 4) Usage (LangGraph CLI)

### A. Start the LangGraph Server

In one terminal, run the LangGraph development server:

```bash
langgraph dev
```

This will start the server, load the `trader` graph, and provide a URL to the LangGraph Studio UI. Keep this server running.

### B. Schedule Trading Decisions (Cron Jobs)

In a second terminal, activate the virtual environment and run the script to create the scheduled jobs:

```bash
source .venv/bin/activate
python scripts/create_crons.py
```

This will register cron jobs with the running server to trigger the trading graph for different instruments and timeframes (e.g., every 5 minutes, every hour).

### C. Monitor

You can monitor the graph runs, view traces, and see the state of the paper broker by inspecting the Studio UI and the `runs/paper_ledger.json` file.

## Notes

*   The trading logic is now triggered by cron jobs managed by the LangGraph server, not a custom Python scheduler.
*   The default configuration runs in a demo mode that does not require any external API keys. To connect to a live broker like OANDA, you will need to update `config/settings.yaml` and provide the necessary credentials in `.env`.
