import sys
import httpx
from langchain_openai import ChatOpenAI
from app.settings import settings


def make_llm() -> ChatOpenAI:
    try:
        llm = ChatOpenAI(
            base_url=settings.llm.base_url,
            api_key="not-used",   # vLLM typically ignores but client expects a key
            model=settings.llm.model,
            temperature=settings.llm.temperature,
            timeout=settings.llm.request_timeout_s,
            max_tokens=settings.llm.max_tokens,
        )
        # Try a simple health check. This is a lightweight call.
        llm.invoke("hello")
        return llm
    except (httpx.ConnectError, Exception) as e:
        print(f"Error connecting to LLM at {settings.llm.base_url}: {e}")
        print("Please ensure your vLLM server is running and accessible.")
        sys.exit(1)
