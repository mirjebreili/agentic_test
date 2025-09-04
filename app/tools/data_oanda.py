import httpx
import pandas as pd
import hashlib
import json
from pathlib import Path

from app.settings import settings
from app.tools.data_models import FeatureSummary
from app.tools.errors import ProviderError
from app.tools.ta_tool import compute_indicators

# Accepts already-valid OANDA granularities like M5, M15, H1, D, W

async def _get(url: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {settings.oanda.api_key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json()

async def candles(instrument: str, granularity: str, count: int = 500) -> FeatureSummary:
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
    df = pd.DataFrame(rows)

    # Add indicators
    df = compute_indicators(df, preset="trend_following")

    # Create cache path and save data
    cache_dir = Path(settings.persistence.get("path", "runs/")) / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    timestamp = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")

    cache_format = settings.data.cache_format
    cache_path = None
    if cache_format != "none":
        if cache_format == "parquet":
            cache_path = cache_dir / f"{instrument}_{granularity}_{timestamp}.parquet"
            try:
                df.to_parquet(cache_path)
            except ImportError:
                raise ProviderError("Parquet engine not found. Please install pyarrow or fastparquet.")
        elif cache_format == "csv":
            cache_path = cache_dir / f"{instrument}_{granularity}_{timestamp}.csv.gz"
            df.to_csv(cache_path, compression="gzip")

    # Create summary
    last_3_closes = df["close"].tail(3).tolist()

    # Get the latest non-NaN indicator values
    latest_indicators = {}
    for col in ["ema_fast", "ema_slow", "atr"]:
        if col in df:
            last_valid = df[col].last_valid_index()
            if last_valid is not None:
                latest_indicators[col] = df.loc[last_valid, col]

    # Create a digest
    summary_data = {
        "instrument": instrument,
        "timeframe": granularity,
        "last_3_closes": last_3_closes,
        "indicators": latest_indicators,
    }
    digest = hashlib.md5(json.dumps(summary_data, sort_keys=True).encode()).hexdigest()

    return FeatureSummary(
        instrument=instrument,
        timeframe=granularity,
        last_n_closes=last_3_closes,
        indicators=latest_indicators,
        cache_path=str(cache_path),
        features_digest=digest,
    )
