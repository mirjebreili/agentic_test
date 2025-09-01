import os
import httpx
from datetime import datetime, timedelta
from app.settings import settings

BASE = "https://finnhub.io/api/v1/news"

async def headlines(category: str = "forex", since_hours: int = 6):
    key = settings.finnhub.get("api_key") if settings.finnhub else os.getenv("FINNHUB_API_KEY")
    _from = (datetime.utcnow() - timedelta(hours=since_hours)).strftime("%Y-%m-%d")
    params = {"category": category, "token": key}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASE, params=params)
        r.raise_for_status()
        return r.json()
