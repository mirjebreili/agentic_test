from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Literal
import yaml
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]

# --- LLM Settings ---
class VLLMSettings(BaseModel):
    base_url: str
    model: str
    api_key: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1024

class OllamaSettings(BaseModel):
    base_url: str
    model: str
    temperature: float = 0.2
    mirostat: int = 0
    num_predict: int = 1024

class LLMSettings(BaseModel):
    provider: str
    vllm: VLLMSettings
    ollama: OllamaSettings

# --- Other Settings ---
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
    account_id: str | None = None
    api_key: str | None = None
    env: Literal["practice", "live"] = "practice"

    @property
    def base(self) -> str:
        return self.practice_base if self.env == "practice" else self.live_base

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
    paper: dict | None = None
    mock_data: dict | None = None
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

    # Resolve OANDA env
    env = data.get("oanda", {}).get("env", os.getenv("OANDA_ENV", "practice")).lower()
    data["oanda"]["env"] = env

    s = Settings(**data)

    return s

try:
    settings = load_settings()
except Exception as e:
    # Use print because logger may depend on settings
    print(f"[config] Failed to load settings: {type(e).__name__}: {e}", flush=True)
    raise  # bubble up so we see the stack
