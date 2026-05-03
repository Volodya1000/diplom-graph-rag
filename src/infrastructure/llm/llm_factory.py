from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config.llm_settings import LLMSettings
from src.config.ollama_settings import OllamaSettings
from src.config.vllm_settings import VLLMSettings


class ChatModelFactory:
    def __init__(self, settings: LLMSettings):
        self._settings = settings

    def create_json(self, temperature: float | None = None) -> BaseChatModel:
        return self._build(temperature=temperature, json_mode=True)

    def create_text(self, temperature: float | None = None) -> BaseChatModel:
        return self._build(temperature=temperature, json_mode=False)

    def _build(self, temperature: float | None, json_mode: bool) -> BaseChatModel:
        s = self._settings
        temp = temperature if temperature is not None else s.temperature

        if isinstance(s, OllamaSettings):
            # Явно указываем тип dict[str, Any] для словаря аргументов
            common_kwargs: dict[str, Any] = {
                "model": s.model_name,
                "base_url": s.get_base_url(),
                "temperature": temp,
                "num_ctx": s.max_tokens,
                "client_kwargs": {"headers": s.get_headers()},
            }

            # Добавляем формат, если нужен JSON
            if json_mode:
                common_kwargs["format"] = "json"

            # Теперь распаковка пройдет без ошибок типизации
            return ChatOllama(**common_kwargs)

        if isinstance(s, VLLMSettings):
            model_kwargs: dict[str, Any] = {"max_tokens": s.max_tokens}
            if json_mode:
                model_kwargs["response_format"] = {"type": "json_object"}

            # Pack arguments into a dictionary to appease the type checker
            openai_kwargs: dict[str, Any] = {
                "model": s.model_name,
                "base_url": s.get_base_url(),
                "api_key": s.api_key if s.api_key else SecretStr("dummy"),
                "temperature": temp,
                "default_headers": s.get_headers(),
                "model_kwargs": model_kwargs,
            }

            return ChatOpenAI(**openai_kwargs)

        raise TypeError(f"Unsupported LLM settings type: {type(s)}")
