# Multiagent Trader (LangGraph Edition)

This project implements a multi-agent FX trading system using the LangGraph framework. It is designed to be run with the LangGraph CLI, providing a powerful development and monitoring experience via the LangGraph Studio.

## Key Architectural Features
- **Unified LLM Interface**: Uses a single OpenAI-compatible client to connect to various LLM backends like VLLM or Ollama.
- **Professional Prompt Management**: All agent prompts are externalized into versioned Markdown files under `app/prompts/`, making them easy to manage, test, and override.
- **Local-First Scheduling**: Uses a simple, robust Python script to trigger graph runs, avoiding dependencies on platform-specific features for local development.
- **Comprehensive Tracing**: Includes a built-in telemetry system that logs detailed traces to local CSV/JSONL files and optionally to LangSmith for cloud-based observability.

## 1. Installation
```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -e .
pip install -U "langgraph-cli[inmem]" langgraph-sdk
```

## 2. Configuration

### 2.1. LLM Backend (vLLM or Ollama)
This project uses a single OpenAI-compatible API to connect to your LLM. You can use either a VLLM server or an Ollama server.

1.  **Create `.env` file:** `cp .env.example .env`
2.  **Edit `.env`:** Configure the `OPENAI_*` variables to point to your chosen backend.

    **For VLLM:**
    ```dotenv
    OPENAI_BASE_URL=http://localhost:8000/v1
    OPENAI_MODEL=Your-vLLM-Model-Name
    ```

    **For Ollama:**
    First, ensure you have a tool-calling capable model (e.g., `ollama pull llama3.1:8b-instruct`). Then, set:
    ```dotenv
    OPENAI_BASE_URL=http://localhost:11434/v1
    OPENAI_MODEL=llama3.1:8b-instruct
    ```

### 2.2. Demo Mode
The default `config/settings.yaml` is configured to run in a fully offline demo mode (`broker_provider: paper`, `data_provider: mock`). No API keys are needed to get started.

## 3. Running the Application

The local workflow uses two terminals: one for the LangGraph server and one for the scheduler script.

### Terminal 1: Start the LangGraph Server
```bash
langgraph dev
```
Keep this server running. It serves the graph and the LangGraph Studio UI.

### Terminal 2: Start the Scheduler
```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the scheduler trigger
python scripts/scheduler_trigger.py
```
This script will connect to the server and begin triggering trading decisions every 60 seconds.

## 4. Prompts
All agent prompts are located in `app/prompts/`. They are versioned `.md` files with a YAML front-matter header.

-   **Structure**: `app/prompts/<agent_name>/<prompt_name>__v<version>.md`
-   **Overrides**: You can override any prompt for a specific environment by creating a file with the same ID in `app/prompts_overrides/<env>/`.
-   **Changelog**: A summary of significant prompt changes can be found in `app/prompts/CHANGELOG.md`.

## 5. Monitoring & Diagnostics
-   **LangGraph Studio**: View traces and debug runs via the URL provided by `langgraph dev`.
-   **Local Traces**: By default, detailed logs are written to `runs/traces/`.
-   **Doctor Script**: Run `python scripts/doctor.py` to check your configuration and connectivity.

For more details on tracing and troubleshooting, see the other sections of this README.
