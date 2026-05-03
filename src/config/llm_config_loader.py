# src/config/llm_config_loader.py
from typing import Literal

from src.config.llm_settings import LLMSettings
from src.config.ollama_settings import OllamaSettings
from src.config.vllm_settings import VLLMSettings


def load_llm_config(provider: Literal["ollama", "vllm"], **kwargs) -> LLMSettings:
    if provider == "ollama":
        return OllamaSettings(**kwargs)
    if provider == "vllm":
        return VLLMSettings(**kwargs)
    raise ValueError(f"Unknown provider: {provider}")
