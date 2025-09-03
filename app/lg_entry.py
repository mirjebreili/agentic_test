from __future__ import annotations

# This factory returns a StateGraph or Compiled graph for the CLI to serve.
# The CLI will import and call this (see langgraph.json mapping).
from langchain_core.runnables import RunnableConfig

def make_graph(config: RunnableConfig | None = None):
    print("[lg_entry] make_graph called")
    # Prefer importing a builder to avoid side effects on import
    from app.graph import build_trader_graph  # implement if missing
    g = build_trader_graph(config or {})
    # If build_trader_graph already compiles, just return g.
    try:
        return g.compile()
    except AttributeError:
        return g
