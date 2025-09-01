import httpx
import pandas as pd
from app.settings import settings

# Accepts already-valid OANDA granularities like M5, M15, H1, D, W

async def _get(url: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {settings.oanda.api_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

async def candles(instrument: str, granularity: str, count: int = 500) -> pd.DataFrame:
    url = f"{settings.oanda.base}/v3/instruments/{instrument}/candles"
    params = {"granularity": granularity, "count": str(count), "price": "M"}
    data = await _get(url, params=params)
    rows = []
    for c in data.get("candles", []):
        if not c.get("complete", False):
            continue
        rows.append({
            "time": pd.to_datetime(c["time"]),
            "open": float(c["mid"]["o"]),
            "high": float(c["mid"]["h"]),
            "low":  float(c["mid"]["l"]),
            "close":float(c["mid"]["c"]),
        })
    return pd.DataFrame(rows)
