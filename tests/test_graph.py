import pytest
from unittest.mock import MagicMock
from langgraph.graph import START, END
from app.graph import build_trader_graph, TraderState, handle_event

@pytest.fixture
def graph():
    """Fixture to build the graph for testing."""
    return build_trader_graph(config={})

def test_build_trader_graph(graph):
    """Test that the graph is built with the correct structure."""
    assert graph is not None
    nodes = list(graph.nodes.keys())
    assert "event_handler" in nodes
    assert "strategy" in nodes
    assert "signal" in nodes
    assert "risk" in nodes
    assert "exec" in nodes

    edges = list(graph.edges)
    assert (START, "event_handler") in edges
    assert ("event_handler", "strategy") in edges
    assert ("strategy", "signal") in edges
    assert ("signal", "risk") in edges
    assert ("risk", "exec") in edges
    assert ("exec", END) in edges

def test_handle_event_node(monkeypatch):
    """Test the handle_event node logic."""
    # Mock the data provider functions to avoid actual data fetching
    mock_candles = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("app.tools.data_mock.candles", mock_candles)

    # Mock settings
    monkeypatch.setattr("app.graph.settings.data_provider", "mock")

    initial_state: TraderState = {
        "messages": [{"role": "user", "content": "CandleCloseEvent EUR_USD M5"}],
        "instrument": "",
        "timeframe": "",
        "candles": None,
    }

    new_state = handle_event(initial_state)

    mock_candles.assert_called_once_with("EUR_USD", "M5", count=200)
    assert new_state["instrument"] == "EUR_USD"
    assert new_state["timeframe"] == "M5"
    assert "candles" in new_state
