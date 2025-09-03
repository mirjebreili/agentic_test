import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from langgraph.graph import END
from langchain_core.messages import ToolMessage
from app.graph import build_trader_graph, get_candles, check_for_tool_error

@pytest.fixture
def graph():
    """Fixture to build the graph for testing, mocking the LLM."""
    with patch('app.graph.make_llm', return_value=MagicMock()):
        graph = build_trader_graph(config={})
        yield graph

def test_build_trader_graph(graph):
    """Test that the graph is built with the correct agent-centric structure."""
    assert graph is not None
    nodes = list(graph.nodes.keys())
    assert "strategy" in nodes
    assert "signal" in nodes
    assert "risk" in nodes
    assert "exec" in nodes

    # The entry point is configured but not easily inspectable without internal knowledge.
    # We trust that set_entry_point works as intended.

    edges = list(graph.edges)
    assert ("signal", "risk") in edges
    assert ("risk", "exec") in edges

    # Check conditional edges
    assert "strategy" in graph.branches
    assert "exec" in graph.branches

@pytest.mark.asyncio
async def test_get_candles_tool_mock_provider(monkeypatch):
    """Test that get_candles tool uses the mock data provider."""
    mock_data_mock_candles = MagicMock(return_value=MagicMock())
    monkeypatch.setattr("app.tools.data_mock.candles", mock_data_mock_candles)

    # Mock the settings to use the mock provider
    monkeypatch.setattr("app.graph.settings.data_provider", "mock")

    # Since get_candles is now a standalone tool, we can invoke it directly
    await get_candles.ainvoke({"instrument": "EUR_USD", "timeframe": "M5"})

    mock_data_mock_candles.assert_called_once_with("EUR_USD", "M5", count=200)

@pytest.mark.asyncio
async def test_get_candles_tool_oanda_provider(monkeypatch):
    """Test that get_candles tool uses the oanda data provider."""
    mock_data_oanda_candles = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr("app.tools.data_oanda.candles", mock_data_oanda_candles)

    monkeypatch.setattr("app.graph.settings.data_provider", "oanda")

    await get_candles.ainvoke({"instrument": "EUR_USD", "timeframe": "M5"})

    mock_data_oanda_candles.assert_called_once_with("EUR_USD", "M5", count=200)

def test_check_for_tool_error_condition():
    """Test the conditional edge logic for routing errors."""
    # Test case where there is an error
    error_state = {
        "messages": [ToolMessage(content='{"error": "Something went wrong"}', tool_call_id="dummy_id")]
    }
    assert check_for_tool_error(error_state) == "error"

    # Test case where there is no error
    success_state = {
        "messages": [ToolMessage(content='{"data": "..."}', tool_call_id="dummy_id")]
    }
    assert check_for_tool_error(success_state) == "continue"
