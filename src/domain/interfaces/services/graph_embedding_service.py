from abc import ABC, abstractmethod


class IEmbeddingService(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        pass

    @abstractmethod
    async def embed_texts_batch(self, texts: list[str]) -> list[list[float]]:
        pass
