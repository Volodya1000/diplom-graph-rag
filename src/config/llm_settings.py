from abc import ABC, abstractmethod


class LLMSettings(ABC):
    model_name: str
    temperature: float
    max_tokens: int

    @abstractmethod
    def get_base_url(self) -> str: ...

    @abstractmethod
    def get_headers(self) -> dict[str, str]: ...
