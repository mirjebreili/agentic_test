import pytest
from app.tools.broker_oanda import _build_order_payload
from app.tools.broker_provider import Order

def test_build_market_order_payload():
    """Verify the payload for a market order is correct."""
    order: Order = {
        "instrument": "EUR_USD",
        "side": "buy",
        "units": 100,
        "entry_type": "market",
        "price": None,
        "stop_loss": 1.1,
        "take_profit": 1.2,
    }
    payload = _build_order_payload(order)
    p_order = payload["order"]

    assert p_order["type"] == "MARKET"
    assert p_order["instrument"] == "EUR_USD"
    assert p_order["units"] == "100"
    assert "price" not in p_order
    assert p_order["stopLossOnFill"]["price"] == "1.1"
    assert p_order["takeProfitOnFill"]["price"] == "1.2"

def test_build_limit_order_payload():
    """Verify the payload for a limit order is correct."""
    order: Order = {
        "instrument": "GBP_USD",
        "side": "sell",
        "units": 2000,
        "entry_type": "limit",
        "price": 1.25,
        "stop_loss": 1.26,
        "take_profit": 1.24,
    }
    payload = _build_order_payload(order)
    p_order = payload["order"]

    assert p_order["type"] == "LIMIT"
    assert p_order["instrument"] == "GBP_USD"
    assert p_order["units"] == "-2000" # sell side is negative
    assert p_order["price"] == "1.25"
    assert p_order["stopLossOnFill"]["price"] == "1.26"
    assert p_order["takeProfitOnFill"]["price"] == "1.24"

def test_payload_no_sl_tp():
    """Verify payload is correct when SL/TP are omitted."""
    order: Order = {
        "instrument": "EUR_USD",
        "side": "buy",
        "units": 100,
        "entry_type": "market",
        "price": None,
        "stop_loss": None,
        "take_profit": None,
    }
    payload = _build_order_payload(order)
    p_order = payload["order"]

    assert "stopLossOnFill" not in p_order
    assert "takeProfitOnFill" not in p_order
