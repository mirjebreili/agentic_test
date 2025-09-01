from __future__ import annotations
import math
from datetime import datetime, time as dtime
from typing import Tuple
import pandas as pd
from app.settings import settings


def within_sessions(now: datetime) -> bool:
    sessions = settings.risk.allowed_sessions
    # Assume broker time ~ UTC for simplicity; adjust if needed
    t = now.time()
    for rng in sessions:
        start_s, end_s = rng.split("-")
        s_h, s_m = map(int, start_s.split(":"))
        e_h, e_m = map(int, end_s.split(":"))
        if dtime(s_h, s_m) <= t <= dtime(e_h, e_m):
            return True
    return False


def position_units(equity: float, risk_pct: float, atr: float, atr_pips: float = 10000.0, pip_value_per_unit: float = 0.0001) -> int:
    # Very rough position sizing: risk = equity * risk_pct, stop ~ atr pips
    # units ≈ risk / (atr_pips * pip_value_per_unit)
    risk_amount = equity * risk_pct
    if atr <= 0:
        return settings.risk.default_units
    denom = (atr * atr_pips * pip_value_per_unit)
    if denom <= 0:
        return settings.risk.default_units
    units = int(max(1, risk_amount / denom))
    return units


def daily_drawdown_ok(current_dd: float) -> bool:
    return current_dd <= settings.risk.max_daily_loss


def guardrails_pass(now: datetime, open_positions: int, daily_dd: float, allow_new_entries: bool) -> Tuple[bool, str]:
    if settings.risk.kill_switch is False:
        return True, "kill_switch_off"
    if not within_sessions(now):
        return False, "outside_session"
    if open_positions >= settings.risk.max_open_positions:
        return False, "max_open_positions"
    if not daily_drawdown_ok(daily_dd):
        return False, "daily_loss_exceeded"
    if not allow_new_entries:
        return False, "macro_throttle"
    return True, "ok"
