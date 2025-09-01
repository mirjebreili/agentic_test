import httpx
from app.settings import settings
from app.tools.broker_provider import Order

async def place_order(order: Order) -> dict:
    # Skip in backtest
    if settings.mode.upper() == "BACKTEST":
        return {"status": "skipped", "reason": "backtest_mode"}

    base = settings.oanda.base
    url = f"{base}/v3/accounts/{settings.oanda.account_id}/orders"
    headers = {
        "Authorization": f"Bearer {settings.oanda.api_key}",
        "Content-Type": "application/json",
    }

    units = order["units"]
    if order["side"].lower() == "sell":
        units = -abs(units)
    else:
        units = abs(units)

    payload: dict = {
        "order": {
            "instrument": order["instrument"],
            "units": str(units),
            "type": "MARKET" if order["entry_type"] == "market" else "LIMIT",
        }
    }
    if order["entry_type"] == "limit" and order.get("price") is not None:
        payload["order"]["price"] = str(order["price"])
    if order.get("stop_loss") is not None:
        payload["order"]["stopLossOnFill"] = {"price": str(order["stop_loss"])}
    if order.get("take_profit") is not None:
        payload["order"]["takeProfitOnFill"] = {"price": str(order["take_profit"])}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()
