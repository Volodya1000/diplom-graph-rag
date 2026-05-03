# src/infrastructure/llm/llm_factory.py
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

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
            if json_mode:
                return ChatOllama(
                    model=s.model_name,
                    base_url=s.get_base_url(),
                    temperature=temp,
                    num_ctx=s.max_tokens,
                    client_kwargs={"headers": s.get_headers()},
                    format="json",
                )
            return ChatOllama(
                model=s.model_name,
                base_url=s.get_base_url(),
                temperature=temp,
                num_ctx=s.max_tokens,
                client_kwargs={"headers": s.get_headers()},
            )
        if isinstance(s, VLLMSettings):
            extra = {"model_kwargs": {"response_format": {"type": "json_object"}}} if json_mode else {}
            return ChatOpenAI(
                model=s.model_name,
                base_url=s.get_base_url(),
                api_key=s.api_key.get_secret_value() if s.api_key else "dummy",
                temperature=temp,
                max_tokens=s.max_tokens,
                default_headers=s.get_headers(),
                **extra,
            )
        raise TypeError(f"Unsupported LLM settings type: {type(s)}")
