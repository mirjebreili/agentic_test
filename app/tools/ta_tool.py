import pandas as pd

try:
    import pandas_ta as ta
except Exception:  # fallback minimal TA
    ta = None


def compute_indicators(df: pd.DataFrame, preset: str) -> pd.DataFrame:
    out = df.copy()
    if ta is None:
        out["ema_fast"] = out["close"].ewm(span=20, adjust=False).mean()
        out["ema_slow"] = out["close"].ewm(span=50, adjust=False).mean()
        out["atr"] = (out["high"] - out["low"]).rolling(14).mean()
        return out

    if preset == "trend_following":
        out["ema_fast"] = ta.ema(out["close"], length=20)
        out["ema_slow"] = ta.ema(out["close"], length=50)
        out["atr"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    elif preset == "mean_reversion":
        bb = ta.bbands(out["close"], length=20)
        out = out.join(bb)
        out["rsi"] = ta.rsi(out["close"], length=14)
        out["atr"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    else:  # default
        out["ema_fast"] = ta.ema(out["close"], length=12)
        out["ema_slow"] = ta.ema(out["close"], length=26)
        out["atr"] = ta.atr(out["high"], out["low"], out["close"], length=14)
    return out
