from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from app.llm import make_llm

# Tools for strategy selection can be added later (e.g., get_candles)
llm = make_llm()

strategy_agent = create_react_agent(
    llm,
    tools=[],
    name="strategy_agent",
    prompt=(
        "You are the Strategy Selector. Given market regime and recent indicators, "
        "choose one preset from: trend_following, mean_reversion, breakout. "
        "Reply JSON only: {\"preset\": <one_of_above>, \"rationale\": <short>}"
    ),
)
