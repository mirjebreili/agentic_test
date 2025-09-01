# Multiagent Trader (LangGraph + vLLM + OANDA)

## 1) Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 2) Start local LLM server (vLLM)

```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000
```

## 3) Configure

* Copy `.env.example` to `.env` and fill values.

## 4) Run (paper trading)

```bash
python -m app_cli.run --mode PAPER
```

## Notes

* Decisions run **on bar close** per timeframe. Price stream & macro throttles are placeholders—fill them next.
* Orders attach server-side SL/TP (if provided) and are skipped in `BACKTEST`.
* Start with OANDA practice. Only later consider LIVE.
