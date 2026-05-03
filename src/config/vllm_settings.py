# src/config/vllm_settings.py
from typing import Literal

from pydantic import BaseModel, SecretStr

from .llm_settings import LLMSettings


class VLLMSettings(BaseModel, LLMSettings):
    provider: Literal["vllm"] = "vllm"
    model_name: str
    temperature: float = 0.1
    max_tokens: int = 8192
    base_url: str = "http://localhost:8000/v1"
    api_key: SecretStr | None = None

    def get_base_url(self) -> str:
        return self.base_url

    def get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}"
        return headers
