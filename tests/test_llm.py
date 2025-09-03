import pytest
from unittest.mock import patch

from app.settings import settings
from app.llm import make_llm

# We test the factory by patching the classes at their source location
@patch('langchain_community.chat_models.ChatOllama')
@patch('langchain_openai.ChatOpenAI')
def test_llm_factory_vllm(mock_openai, mock_ollama, monkeypatch):
    """Test that the factory calls ChatOpenAI for the 'vllm' provider."""
    monkeypatch.setattr(settings.llm, "provider", "vllm")

    make_llm()

    mock_openai.assert_called_once()
    mock_ollama.assert_not_called()

@patch('langchain_community.chat_models.ChatOllama')
@patch('langchain_openai.ChatOpenAI')
def test_llm_factory_ollama(mock_openai, mock_ollama, monkeypatch):
    """Test that the factory calls ChatOllama for the 'ollama' provider."""
    monkeypatch.setattr(settings.llm, "provider", "ollama")

    make_llm()

    mock_openai.assert_not_called()
    mock_ollama.assert_called_once()

def test_llm_factory_unsupported_provider(monkeypatch):
    """Test that the factory raises an error for an unsupported provider."""
    monkeypatch.setattr(settings.llm, "provider", "unsupported_provider")

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        make_llm()
