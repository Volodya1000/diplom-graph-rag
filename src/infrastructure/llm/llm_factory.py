"""
Единственное место создания ChatOllama.

Устраняет дублирование конструктора в трёх клиентах.
Фабрика — инфраструктурная деталь, доменные интерфейсы
(ILLMClient, IAnswerGenerator, ISynonymResolver) о ней не знают.
"""

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from src.config.ollama_settings import OllamaSettings

logger = logging.getLogger(__name__)


class ChatOllamaFactory:
    """Фабрика для создания сконфигурированных ChatOllama."""

    def __init__(self, settings: OllamaSettings):
        self._settings = settings
        logger.info(
            f"🔌 LLM Factory | model={settings.model_name} "
            f"| cloud={settings.is_cloud} "
            f"| url={settings.base_url}"
        )

    def create_json(
        self,
        temperature: Optional[float] = None,
    ) -> BaseChatModel:
        """ChatOllama с format='json' — для структурированных ответов."""
        return self._build(
            temperature=temperature,
            json_mode=True,
        )

    def create_text(
        self,
        temperature: Optional[float] = None,
    ) -> BaseChatModel:
        """ChatOllama без json — для свободного текста."""
        return self._build(
            temperature=temperature,
            json_mode=False,
        )

    def _build(
        self,
        temperature: Optional[float],
        json_mode: bool,
    ) -> ChatOllama:
        s = self._settings
        kwargs = dict(
            model=s.model_name,
            base_url=s.base_url,
            temperature=temperature if temperature is not None else s.temperature,
            num_ctx=s.num_ctx,
            client_kwargs={"headers": s.headers},
            verbose=False,
        )
        if json_mode:
            kwargs["format"] = "json"
        return ChatOllama(**kwargs)