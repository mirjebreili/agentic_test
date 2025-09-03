from langchain_core.language_models.chat_models import BaseChatModel
from app.settings import settings

def make_llm() -> BaseChatModel:
    """
    Factory function to create an LLM client based on the provider specified in the settings.
    """
    provider = settings.llm.provider.lower()

    print(f"--- Creating LLM client for provider: {provider} ---")

    if provider == "vllm":
        from langchain_openai import ChatOpenAI
        cfg = settings.llm.vllm
        return ChatOpenAI(
            base_url=cfg.base_url,
            api_key=cfg.api_key or "not-used",
            model=cfg.model,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        cfg = settings.llm.ollama
        return ChatOllama(
            base_url=cfg.base_url,
            model=cfg.model,
            temperature=cfg.temperature,
            mirostat=cfg.mirostat,
            num_predict=cfg.num_predict,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm.provider}")
