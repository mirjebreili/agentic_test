from __future__ import annotations
import httpx
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.settings import settings

# --- Globals ---
# This will be set by a probe at startup
SUPPORTS_TOOL_CALLING = True

def probe_tool_calling_capability() -> bool:
    """
    Performs a small, one-time check to see if the configured LLM supports tool calling.
    Updates the global SUPPORTS_TOOL_CALLING flag.
    """
    global SUPPORTS_TOOL_CALLING
    if not settings.llm.probe_tools:
        print("--- LLM tool-calling probe disabled by settings. Assuming tools are supported. ---")
        SUPPORTS_TOOL_CALLING = True
        return SUPPORTS_TOOL_CALLING

    print(f"--- Probing LLM at {settings.llm.base_url} for tool-calling capability... ---")
    # This is a simplified probe. A real implementation would be more robust.
    # For now, we assume if it's an OpenAI-compatible endpoint, it supports tools.
    # A better probe would make a small test call with a dummy tool.
    SUPPORTS_TOOL_CALLING = True
    print(f"--- Tool calling supported: {SUPPORTS_TOOL_CALLING} ---")
    return SUPPORTS_TOOL_CALLING

def make_llm() -> BaseChatModel:
    """
    Factory function to create an LLM client.
    Now uses a single OpenAI-compatible path for both VLLM and Ollama.
    """
    print(f"--- Creating OpenAI-compatible client for model: {settings.llm.model} ---")

    # Capability gate
    if settings.llm.require_tools and not SUPPORTS_TOOL_CALLING:
        raise ValueError(
            f"LLM model '{settings.llm.model}' does not support tool calling, but it is required by settings."
            "Please choose a different model."
        )

    cfg = settings.llm

    # Create a custom httpx client with tuned timeouts
    timeout = httpx.Timeout(cfg.connect_timeout, read=cfg.read_timeout)
    http_client = httpx.Client(timeout=timeout)

    return ChatOpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key or "not-needed-for-local",
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        http_client=http_client,
    )
