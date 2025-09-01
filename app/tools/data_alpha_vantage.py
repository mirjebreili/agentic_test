import os
import httpx
import pandas as pd
from app.settings import settings

BASE = "https://www.alphavantage.co/query"

async def fx_daily(from_symbol: str, to_symbol: str) -> pd.DataFrame:
    key = settings.alpha_vantage.get("api_key") if settings.alpha_vantage else os.getenv("ALPHA_VANTAGE_KEY")
    params = {
        "function": "FX_DAILY",
        "from_symbol": from_symbol,
        "to_symbol": to_symbol,
        "apikey": key,
        "outputsize": settings.alpha_vantage.get("outputsize", "compact") if settings.alpha_vantage else "compact",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASE, params=params)
        r.raise_for_status()
        data = r.json().get("Time Series FX (Daily)", {})
    rows = []
    for ts, ohlc in data.items():
        rows.append({
            "time": pd.to_datetime(ts),
            "open": float(ohlc["1. open"]),
            "high": float(ohlc["2. high"]),
            "low": float(ohlc["3. low"]),
            "close": float(ohlc["4. close"]),
        })
    return pd.DataFrame(rows).sort_values("time")
