import pytest
from datetime import datetime
from app.tools.risk_tool import position_units, guardrails_pass
from app.settings import settings

def test_position_units_basic():
    """Test basic position unit calculation."""
    units = position_units(equity=100_000, risk_pct=0.01, atr=0.0050)
    assert isinstance(units, int)
    # Calculation:
    # risk_amount = 100_000 * 0.01 = 1000
    # denom = atr * atr_pips * pip_value_per_unit = 0.0050 * 10000.0 * 0.0001 = 0.005
    # units = risk_amount / denom = 1000 / 0.005 = 200_000
    assert units == 200000

def test_position_units_zero_atr():
    """Test that zero ATR falls back to default units."""
    units = position_units(equity=100_000, risk_pct=0.01, atr=0)
    assert units == settings.risk.default_units

def test_guardrails_pass():
    """Test scenarios where guardrails should pass."""
    now = datetime(2024, 1, 1, 10, 0) # within 07:00-21:00
    ok, reason = guardrails_pass(now, open_positions=1, daily_dd=0.01, allow_new_entries=True)
    assert ok is True
    assert reason == "ok"

def test_guardrails_fail_session():
    """Test guardrail failure due to being outside allowed session."""
    now = datetime(2024, 1, 1, 22, 0) # outside 07:00-21:00
    ok, reason = guardrails_pass(now, open_positions=1, daily_dd=0.01, allow_new_entries=True)
    assert ok is False
    assert reason == "outside_session"

def test_guardrails_fail_max_positions():
    """Test guardrail failure due to max open positions."""
    now = datetime(2024, 1, 1, 10, 0)
    max_pos = settings.risk.max_open_positions
    ok, reason = guardrails_pass(now, open_positions=max_pos, daily_dd=0.01, allow_new_entries=True)
    assert ok is False
    assert reason == "max_open_positions"

def test_guardrails_fail_daily_loss():
    """Test guardrail failure due to exceeding max daily loss."""
    now = datetime(2024, 1, 1, 10, 0)
    max_loss = settings.risk.max_daily_loss
    ok, reason = guardrails_pass(now, open_positions=1, daily_dd=max_loss + 0.01, allow_new_entries=True)
    assert ok is False
    assert reason == "daily_loss_exceeded"

def test_guardrails_fail_macro_throttle():
    """Test guardrail failure due to macro event throttle."""
    now = datetime(2024, 1, 1, 10, 0)
    ok, reason = guardrails_pass(now, open_positions=1, daily_dd=0.01, allow_new_entries=False)
    assert ok is False
    assert reason == "macro_throttle"
