from __future__ import annotations

import structlog
from langchain_core.language_models import BaseChatModel

from biblio_checker_worker.core.config import get_settings

logger = structlog.stdlib.get_logger("biblio_checker_worker.langgraph.clients.llm")


def get_llm() -> BaseChatModel:
    """Return a configured LLM instance based on LLM_PROVIDER setting.

    Reads settings at call time — no module-level caching — so that tests can
    override settings between calls and configuration changes take effect without
    restarting the process.

    Raises:
        ValueError: If ``settings.llm_provider`` is not ``"anthropic"`` or ``"openai"``.
    """
    settings = get_settings()
    provider = settings.llm_provider
    model = settings.llm_model
    temperature = settings.llm_temperature

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        llm: BaseChatModel = ChatAnthropic(
            model=model,
            temperature=temperature,
            anthropic_api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=4096,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=settings.openai_api_key.get_secret_value(),
        )
    else:
        raise ValueError(f"Unsupported llm_provider: {provider}")

    logger.info(
        "llm_client_created",
        provider=provider,
        model=model,
        temperature=temperature,
    )
    return llm
