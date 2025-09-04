import pytest
from unittest.mock import MagicMock, patch
from langgraph.graph import END
from langchain_core.tools import tool, StructuredTool
from langchain_core.messages import HumanMessage, AIMessage

from app.graph import build_trader_graph, TraderState

# This file tests the graph construction and routing logic.
# It uses a behavioral testing approach, as recommended for LangGraph.
# Instead of asserting the graph's internal structure (which is brittle),
# we inject deterministic routers and mock tools to verify that the graph
# follows the expected execution paths under different conditions.

@pytest.fixture
def fake_toolset():
    """A fixture that provides a complete set of fake tools for injection."""
    @tool
    def fake_get_candles(instrument: str, timeframe: str):
        """A fake get_candles tool."""
        return f"Candles for {instrument} {timeframe}"

    @tool
    def fake_propose_order(instrument: str, action: str):
        """A fake propose_order tool."""
        return {"instrument": instrument, "action": action, "stops": None}

    @tool
    def fake_attach_stops(order: dict):
        """A fake attach_stops tool."""
        order["stops"] = {"sl": 0.9, "tp": 1.1}
        return order

    @tool
    def fake_execute_order(order: dict):
        """A fake execute_order tool."""
        return {"status": "success", "order_id": "fake_123"}

    # The @tool decorator already converts these to StructuredTool instances.
    return [
        fake_get_candles,
        fake_propose_order,
        fake_attach_stops,
        fake_execute_order,
    ]

def run_graph_and_get_node_sequence(graph, initial_state):
    """Helper function to run the graph and capture the sequence of visited nodes."""
    sequence = []
    # A graph must be compiled before it can be streamed.
    app = graph.compile()
    # The 'updates' stream_mode returns a dict with the node name as the key
    for node in app.stream(initial_state, stream_mode="updates"):
        node_name = list(node.keys())[0]
        sequence.append(node_name)
    return sequence

def test_graph_happy_path(fake_toolset):
    """
    Tests the 'happy path' where the graph proceeds through all main nodes
    (strategy -> signal -> risk -> exec -> END).
    We inject routers that always return 'continue' to force this path.
    """
    route_overrides = {
        "strategy": lambda state: "continue",
        "signal": lambda state: "continue",
        "risk": lambda state: "continue",
        "exec": lambda state: "continue",
    }

    # We now patch the agent factory itself to return a mock agent.
    # This mock agent, when invoked, returns the desired message structure.
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"messages": [AIMessage(content="mocked agent response")]}

    with patch('app.graph.create_react_agent', return_value=mock_agent):
        graph = build_trader_graph(
            config={},
            tools=fake_toolset,
            route_overrides=route_overrides
        )

    initial_state = {"messages": [HumanMessage(content="Start")]}
    sequence = run_graph_and_get_node_sequence(graph, initial_state)

    # The 'updates' stream does not include the final __end__ node.
    expected_sequence = ["strategy", "signal", "risk", "exec"]
    assert sequence == expected_sequence

def test_graph_early_exit(fake_toolset):
    """
    Tests a scenario where the graph exits early from the 'strategy' node.
    We inject a router for 'strategy' that returns 'error', which should
    route to the error handler and then to the end.
    """
    # The 'error' branch is hardcoded to go to the 'error_handler' node.
    route_overrides = {
        "strategy": lambda state: "error",
    }

    # We now patch the agent factory itself to return a mock agent.
    # This mock agent, when invoked, returns the desired message structure.
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"messages": [AIMessage(content="mocked agent response")]}

    with patch('app.graph.create_react_agent', return_value=mock_agent):
        graph = build_trader_graph(
            config={},
            tools=fake_toolset,
            route_overrides=route_overrides
        )

    initial_state = {"messages": [HumanMessage(content="Start")]}
    sequence = run_graph_and_get_node_sequence(graph, initial_state)

    expected_sequence = ["strategy", "error_handler"]
    assert sequence == expected_sequence
