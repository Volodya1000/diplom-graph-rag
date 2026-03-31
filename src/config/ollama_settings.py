from typing import Dict, Optional
from pydantic import BaseModel, SecretStr


class OllamaSettings(BaseModel):
    model_name: str
    temperature: float
    num_ctx: int
    is_cloud: bool
    local_url: str
    api_key: Optional[SecretStr] = None

    @property
    def base_url(self) -> str:
        if self.is_cloud:
            return "https://ollama.com"
        return self.local_url

    @property
    def headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.is_cloud and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}"
        return headers
