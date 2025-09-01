from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from app.llm import make_llm

llm = make_llm()

signal_agent = create_react_agent(
    llm,
    tools=[],
    name="signal_agent",
    prompt=(
        "You are the Signal Agent. Using the chosen preset and latest indicators, "
        "produce a trading signal. Reply strict JSON: {\"action\": "
        "\"buy\"|\"sell\"|\"hold\", \"instrument\": str, \"timeframe\": str, "
        "\"units\": int, \"entry_type\": \"market\"|\"limit\", \"price\": number|null}"
    ),
)
