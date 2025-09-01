from __future__ import annotations
import os
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]

class LLMSettings(BaseModel):
    base_url: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 1024
    request_timeout_s: int = 30

class RiskSettings(BaseModel):
    max_risk_per_trade: float
    max_daily_loss: float
    max_open_positions: int
    allowed_sessions: list[str]
    kill_switch: bool = True
    default_units: int = 1000
    sl_buffer_atr: float = 1.5
    tp_buffer_atr: float = 2.5

class OandaSettings(BaseModel):
    practice_base: str
    live_base: str
    account_id: str
    api_key: str
    env: str  # practice | live

class SchedulerSettings(BaseModel):
    decisions: list[dict]
    heartbeat_every_seconds: int = 60
    price_stream: dict | None = None
    macro_throttle: dict | None = None

class Settings(BaseModel):
    app: dict
    llm: LLMSettings
    mode: str
    data_provider: str
    broker_provider: str
    news_provider: str | None
    macro_provider: str | None
    instruments: list[str]
    timeframes: list[str]
    scheduler: SchedulerSettings
    risk: RiskSettings
    oanda: OandaSettings
    alpha_vantage: dict | None = None
    finnhub: dict | None = None
    twelve_data: dict | None = None
    trading_economics: dict | None = None
    backtest: dict | None = None
    logging: dict | None = None
    persistence: dict | None = None


def _expand_env(content: str) -> str:
    # Allow ${VAR} expansion from OS env vars
    return os.path.expandvars(content)


def load_settings() -> Settings:
    cfg_path = ROOT / "config" / "settings.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        raw = _expand_env(f.read())
    data: dict[str, Any] = yaml.safe_load(raw)

    # Resolve OANDA base by env
    env = data.get("oanda", {}).get("env", os.getenv("OANDA_ENV", "practice")).lower()
    base = data["oanda"]["practice_base"] if env == "practice" else data["oanda"]["live_base"]
    data["oanda"]["env"] = env
    data["oanda"]["base"] = base

    s = Settings(**data)

    if s.mode.upper() in ["PAPER", "LIVE"]:
        if not s.oanda.api_key or s.oanda.api_key == "replace_me":
            raise ValueError("OANDA_API_KEY must be set in .env for PAPER or LIVE mode")
        if not s.oanda.account_id or s.oanda.account_id == "replace_me":
            raise ValueError("OANDA_ACCOUNT_ID must be set in .env for PAPER or LIVE mode")

    return s

try:
    settings = load_settings()
except ValueError as e:
    import sys
    print(f"Error loading settings: {e}")
    sys.exit(1)
