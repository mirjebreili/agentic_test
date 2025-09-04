import pytest
from app.settings import load_settings

@pytest.fixture(autouse=True)
def set_required_env_vars(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OANDA_API_KEY", "test-key")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "test-account")
    monkeypatch.setenv("MODE", "BACKTEST") # Default to a mode that doesn't require keys

def test_settings_load_practice(monkeypatch):
    """Verify settings load correctly for practice environment."""
    monkeypatch.setenv("OANDA_ENV", "practice")
    settings = load_settings()
    assert settings.oanda.env == "practice"
    assert settings.oanda.base == "https://api-fxpractice.oanda.com"
    assert settings.llm.base_url == "http://localhost:8000/v1"
    assert settings.llm.model == "test-model"

def test_settings_load_live(monkeypatch):
    """Verify settings load correctly for live environment."""
    monkeypatch.setenv("OANDA_ENV", "live")
    settings = load_settings()
    assert settings.oanda.env == "live"
    assert settings.oanda.base == "https://api-fxtrade.oanda.com"

def test_settings_ok_with_missing_keys_in_backtest_mode(monkeypatch):
    """Verify settings load succeeds if keys are missing in BACKTEST mode."""
    monkeypatch.setenv("MODE", "BACKTEST")
    monkeypatch.setenv("OANDA_API_KEY", "replace_me")
    try:
        load_settings()
    except ValueError:
        pytest.fail("load_settings() raised ValueError unexpectedly in BACKTEST mode")
