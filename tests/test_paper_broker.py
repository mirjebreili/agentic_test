from app.tools.broker_paper import PaperBroker
from app.tools.data_mock import candles

def test_paper_flow_smoke():
    brk = PaperBroker()
    brk.reset()  # start clean

    # place a market buy
    res = brk.place_order({
        "instrument": "EUR_USD",
        "side": "buy",
        "units": 1000,
        "entry_type": "market",
        "price": None,
        "stop_loss": 1.05,
        "take_profit": 1.20,
    })
    assert res["status"] == "accepted"

    # advance one synthetic bar to fill the market order
    df = candles("EUR_USD", "M5", 2)
    last = df.iloc[-1]
    brk.on_bar("EUR_USD", float(last.open), float(last.high), float(last.low), float(last.close))

    snap = brk.snapshot()
    assert "positions" in snap and isinstance(snap["positions"], dict)
    assert len(snap["history"]) == 1
    assert snap["history"][0]["status"] == "open"

def test_paper_broker_stop_loss():
    brk = PaperBroker()
    brk.reset()

    # Place a market buy with a stop loss
    stop_loss_price = 1.10
    res = brk.place_order({
        "instrument": "EUR_USD",
        "side": "buy",
        "units": 1000,
        "entry_type": "market",
        "price": None,
        "stop_loss": stop_loss_price,
        "take_profit": 1.20,
    })
    assert res["status"] == "accepted"

    # First bar to open the position
    brk.on_bar("EUR_USD", o=1.12, h=1.13, l=1.11, c=1.12)
    snap = brk.snapshot()
    assert snap["history"][0]["status"] == "open"

    # Second bar to trigger the stop loss
    brk.on_bar("EUR_USD", o=1.11, h=1.11, l=1.09, c=1.10)
    snap = brk.snapshot()
    assert len(snap["positions"]) == 0 # Position should be closed
    assert snap["history"][0]["status"] == "closed"
    assert snap["history"][0]["close_reason"] == "stop_loss"
    assert snap["history"][0]["close_price"] == stop_loss_price
