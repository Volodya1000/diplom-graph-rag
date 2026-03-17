import os
from typing import Dict, Optional
from pydantic import BaseModel, Field


class OllamaSettings(BaseModel):
    """
    Настройки модели Ollama с переключателем Cloud/Local.
    """
    model_name: str = Field(default="qwen3.5:9b", description="Название модели")
    temperature: float = Field(default=0.4, ge=0.0, le=1.0)
    num_ctx: int = Field(default=4096, ge=1024)
    is_cloud: bool = Field(default=False)

    # API ключ (читается один раз из .env)
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("OLLAMA_API_KEY")
    )

    @property
    def base_url(self) -> str:
        if self.is_cloud:
            return "https://ollama.com"          # ← замени на свой облачный endpoint если нужно
        return os.getenv("OLLAMA_LOCAL_URL", "http://localhost:11434")

    @property
    def headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.is_cloud and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers