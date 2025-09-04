import pytest
import os
from unittest.mock import patch, MagicMock

from app.settings import settings
from app.llm import make_llm, probe_tool_calling_capability

@patch('app.llm.ChatOpenAI')
def test_make_llm_creates_openai_client(mock_chat_openai):
    """Test that make_llm always creates a ChatOpenAI client."""
    # We need to reload the settings module to apply monkeypatches for tests
    with patch.dict(os.environ, {"LLM_PROVIDER": "vllm"}):
        from app.settings import load_settings
        settings = load_settings()

        from app.llm import make_llm
        llm = make_llm()
        mock_chat_openai.assert_called_once()
        assert llm == mock_chat_openai.return_value

@patch('app.llm.SUPPORTS_TOOL_CALLING', False)
def test_capability_gate_fails_if_tools_required(monkeypatch):
    """Test that make_llm fails if tools are required but not supported."""
    monkeypatch.setattr(settings.llm, "require_tools", True)
    from app.llm import make_llm

    with pytest.raises(ValueError, match="does not support tool calling"):
        make_llm()

@patch('app.llm.SUPPORTS_TOOL_CALLING', False)
def test_capability_gate_passes_if_tools_not_required(monkeypatch):
    """Test that make_llm succeeds if tools are not required and not supported."""
    monkeypatch.setattr(settings.llm, "require_tools", False)
    from app.llm import make_llm

    try:
        make_llm()
    except ValueError:
        pytest.fail("make_llm should not have raised a ValueError.")

def test_probe_disabled_by_setting(monkeypatch):
    """Test that the tool probe is disabled if the setting is false."""
    monkeypatch.setattr(settings.llm, "probe_tools", False)
    from app.llm import probe_tool_calling_capability

    assert probe_tool_calling_capability() is True
