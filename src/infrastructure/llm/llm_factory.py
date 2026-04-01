"""
Единственное место создания ChatOllama.
"""

import logging
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from src.config.ollama_settings import OllamaSettings

logger = logging.getLogger(__name__)


class ChatOllamaFactory:
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
        return self._build(temperature=temperature, json_mode=True)

    def create_text(
        self,
        temperature: Optional[float] = None,
    ) -> BaseChatModel:
        return self._build(temperature=temperature, json_mode=False)

    def _build(
        self,
        temperature: Optional[float],
        json_mode: bool,
    ) -> ChatOllama:
        s = self._settings
        temp = temperature if temperature is not None else s.temperature
        if json_mode:
            return ChatOllama(
                model=s.model_name,
                base_url=s.base_url,
                temperature=temp,
                num_ctx=s.num_ctx,
                client_kwargs={"headers": s.headers},
                format="json",
                verbose=False,
            )
        return ChatOllama(
            model=s.model_name,
            base_url=s.base_url,
            temperature=temp,
            num_ctx=s.num_ctx,
            client_kwargs={"headers": s.headers},
            verbose=False,
        )
