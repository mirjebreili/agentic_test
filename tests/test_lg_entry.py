import pytest
from unittest.mock import patch, MagicMock
from app.lg_entry import make_graph

@patch('app.graph.build_trader_graph')
def test_make_graph(mock_build_trader_graph):
    """Test that the make_graph factory function returns a compiled graph."""
    # Configure the mock to return an object that has a `compile` method
    mock_graph = MagicMock()
    mock_build_trader_graph.return_value = mock_graph

    # Call the factory function
    compiled_graph = make_graph()

    # Assert that build_trader_graph was called
    mock_build_trader_graph.assert_called_once()

    # Assert that compile was called on the returned graph object
    mock_graph.compile.assert_called_once()

    # Assert that the final result is the compiled graph
    assert compiled_graph == mock_graph.compile.return_value
