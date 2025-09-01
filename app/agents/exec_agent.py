from langgraph.prebuilt import create_react_agent
from app.llm import make_llm

llm = make_llm()

exec_agent = create_react_agent(
    llm,
    tools=[],
    name="exec_agent",
    prompt=(
        "You are the Execution Agent. If guardrails pass and mode allows, execute the order via broker. "
        "Otherwise, explain why skipped. Return broker JSON response or a JSON error with reason."
    ),
)
