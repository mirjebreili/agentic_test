import os
import sys
import httpx
from unittest.mock import MagicMock
from langchain_openai import ChatOpenAI
from app.settings import settings


def make_llm() -> ChatOpenAI:
    # In a test environment, return a mock object to avoid actual LLM calls.
    if "PYTEST_CURRENT_TEST" in os.environ:
        return MagicMock(spec=ChatOpenAI)

    try:
        llm = ChatOpenAI(
            base_url=settings.llm.base_url,
            api_key="not-used",   # vLLM typically ignores but client expects a key
            model=settings.llm.model,
            temperature=settings.llm.temperature,
            timeout=settings.llm.request_timeout_s,
            max_tokens=settings.llm.max_tokens,
        )
        # A simple health check is too slow, rely on user to have it running.
        # llm.invoke("hello")
        return llm
    except (httpx.ConnectError, Exception) as e:
        # Raise a catchable exception instead of exiting directly
        raise ConnectionError(
            f"Error connecting to LLM at {settings.llm.base_url}: {e}. "
            "Please ensure your vLLM server is running and accessible."
        )
