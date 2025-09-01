import os
import httpx
from datetime import datetime, timedelta
from app.settings import settings

BASE = "https://api.tradingeconomics.com/calendar"

async def upcoming(high_impact_only: bool = True, window_hours: int = 6) -> list[dict]:
    key = settings.trading_economics.get("api_key") if settings.trading_economics else os.getenv("TE_KEY")
    start = datetime.utcnow().strftime("%Y-%m-%d")
    end = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")
    params = {"c": key, "format": "json", "d1": start, "d2": end}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASE, params=params)
        r.raise_for_status()
        items = r.json()
    if high_impact_only:
        items = [x for x in items if str(x.get("Importance", "")).lower() in {"high", "3"}]
    return items
