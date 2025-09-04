import pytest
from unittest.mock import MagicMock, patch
import json

from app.tools.standard import get_candles, execute_order, propose_order, attach_stops
from app.tools.data_models import FeatureSummary
from app.tools.errors import ProviderError

@pytest.mark.asyncio
async def test_get_candles_mock(monkeypatch):
    """Test get_candles with the mock data provider."""
    mock_summary = FeatureSummary(
        instrument="EUR_USD",
        timeframe="M5",
        last_n_closes=[1.0, 1.1, 1.2],
        indicators={"ema": 1.1},
        cache_path="/fake/path.parquet",
        features_digest="abc"
    )

    mock_data_mock_candles = MagicMock(return_value=mock_summary)
    monkeypatch.setattr("app.tools.standard.settings.data.provider", "mock")
    monkeypatch.setattr("app.tools.data_mock.candles", mock_data_mock_candles)
    monkeypatch.setattr("app.tools.broker_paper.PaperBroker", MagicMock())

    result = await get_candles.ainvoke({"instrument": "EUR_USD", "timeframe": "M5"})

    mock_data_mock_candles.assert_called_once()
    assert json.loads(result) == json.loads(mock_summary.model_dump_json())

def test_propose_order():
    """Test that propose_order returns a correctly structured dict."""
    result = propose_order.invoke({"instrument": "EUR_USD", "side": "buy", "units": 1000, "entry_type": "market"})
    assert result["instrument"] == "EUR_USD"
    assert result["side"] == "buy"
    assert result["units"] == 1000

def test_attach_stops():
    """Test that attach_stops correctly adds SL/TP to an order."""
    order = {"price": 1.1000}
    result = attach_stops.invoke({"order": order, "atr": 0.0050, "sl_mult": 1.5, "tp_mult": 2.0})
    assert "stop_loss" in result
    assert "take_profit" in result
    assert result["stop_loss"] == pytest.approx(1.0925)
    assert result["take_profit"] == pytest.approx(1.1100)
