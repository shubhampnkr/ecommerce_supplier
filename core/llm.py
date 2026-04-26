"""
LLM factory – returns a LangChain chat model based on settings.
"""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import settings
from core.logger import logger


def get_llm(temperature: float | None = None) -> BaseChatModel:
    temp = temperature if temperature is not None else settings.llm_temperature

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        logger.info(f"Using Anthropic model: {settings.llm_model_anthropic}")
        return ChatAnthropic(
            model=settings.llm_model_anthropic,
            api_key=settings.anthropic_api_key,
            temperature=temp,
            max_tokens=4096,
        )  # type: ignore

    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        logger.info(f"Using OpenAI model: {settings.llm_model_openai}")
        return ChatOpenAI(
            model=settings.llm_model_openai,
            api_key=settings.openai_api_key,
            temperature=temp,
        )  # type: ignore

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
