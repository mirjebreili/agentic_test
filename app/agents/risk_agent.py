from langgraph.prebuilt import create_react_agent
from app.llm import make_llm

llm = make_llm()

risk_agent = create_react_agent(
    llm,
    tools=[],
    name="risk_agent",
    prompt=(
        "You are the Risk Agent. Take a proposed order and attach stop_loss and take_profit "
        "using ATR multiples from config (sl_buffer_atr, tp_buffer_atr). Ensure units are sane. "
        "Reply strict JSON matching: {instrument, side, units, entry_type, price, stop_loss, take_profit}."
    ),
)
