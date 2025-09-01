from __future__ import annotations

"""
Mock Data Provider — synthetic or CSV-based candles for demos/tests.

- synthetic: generates OHLC using a simple GBM process (reproducible via seed).
- csv: loads OHLC from local CSV files per instrument.

Returns a pandas.DataFrame with columns: time, open, high, low, close
(similar to OANDA candles shape used elsewhere in the app).
"""

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from app.settings import settings


def _from_csv(instrument: str, count: int) -> pd.DataFrame:
    cfg: Dict = getattr(settings, "mock_data", {}) or {}
    file_map: Dict = cfg.get("csv_files", {}) or {}
    path = Path(file_map.get(instrument, ""))

    if not path.exists():
        # Return empty DF with the expected columns
        return pd.DataFrame(columns=["time", "open", "high", "low", "close"])

    df = pd.read_csv(path)
    # Accept flexible column casing; map to standard names
    cols = {c.lower(): c for c in df.columns}
    for required in ("time", "open", "high", "low", "close"):
        if required not in cols:
            raise ValueError(f"CSV {path} is missing required column: {required}")

    out = pd.DataFrame(
        {
            "time": pd.to_datetime(df[cols["time"]]),
            "open": pd.to_numeric(df[cols["open"]], errors="coerce").astype(float),
            "high": pd.to_numeric(df[cols["high"]], errors="coerce").astype(float),
            "low": pd.to_numeric(df[cols["low"]], errors="coerce").astype(float),
            "close": pd.to_numeric(df[cols["close"]], errors="coerce").astype(float),
        }
    ).dropna()
    # Keep the most recent `count` rows
    return out.tail(count).reset_index(drop=True)


def _synthetic(instrument: str, count: int) -> pd.DataFrame:
    cfg: Dict = getattr(settings, "mock_data", {}) or {}
    seed = int(cfg.get("seed", 42))
    drift = float(cfg.get("drift", 0.0))   # daily drift
    vol = float(cfg.get("vol", 0.01))      # daily vol

    rng = np.random.default_rng(seed)
    n = int(max(2, count))
    # Use a plausible starting level by instrument
    s0 = 1.10 if instrument == "EUR_USD" else 1.27
    # Treat each step as ~5 minutes (288 steps/day)
    dt = 1.0 / 288.0
    rets = (drift - 0.5 * vol * vol) * dt + vol * np.sqrt(dt) * rng.standard_normal(n)
    close = s0 * np.exp(np.cumsum(rets))
    open_ = np.r_[close[0], close[:-1]]  # previous close
    # Build a small range around open/close for H/L
    high = np.maximum(open_, close) * (1 + 0.0005 * rng.random(n))
    low = np.minimum(open_, close) * (1 - 0.0005 * rng.random(n))
    t = pd.date_range(end=pd.Timestamp.utcnow(), periods=n, freq="5min")

    out = pd.DataFrame(
        {"time": t, "open": open_, "high": high, "low": low, "close": close}
    )
    return out.reset_index(drop=True)


def candles(instrument: str, granularity: str, count: int = 500) -> pd.DataFrame:
    """
    Return a DataFrame of recent candles for `instrument`.
    `granularity` is currently ignored (we emit ~5-minute bars).
    """
    cfg: Dict = getattr(settings, "mock_data", {}) or {}
    source = str(cfg.get("source", "synthetic")).lower()
    if source == "csv":
        return _from_csv(instrument, count)
    return _synthetic(instrument, count)
