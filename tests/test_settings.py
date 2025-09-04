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
    assert settings.llm.provider_label == "OPENAI_COMPAT"

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

def test_llm_provider_label_from_env_var(monkeypatch):
    """Verify LLM provider label is set from the LLM_PROVIDER env var."""
    import os
    monkeypatch.setenv("LLM_PROVIDER", "OLLAMA")
    assert os.getenv("LLM_PROVIDER") == "OLLAMA" # Check if monkeypatch works
    settings = load_settings()
    assert settings.llm.provider_label == "OLLAMA"

def test_llm_provider_label_inference_from_url(monkeypatch):
    """Verify LLM provider label is inferred from the base URL."""
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    settings = load_settings()
    assert settings.llm.provider_label == "OLLAMA"

def test_llm_provider_label_defaults_to_compat(monkeypatch):
    """Verify LLM provider label defaults to OPENAI_COMPAT for other URLs."""
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
    settings = load_settings()
    assert settings.llm.provider_label == "OPENAI_COMPAT"
