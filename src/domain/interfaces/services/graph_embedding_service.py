from abc import ABC, abstractmethod
from typing import List

class IEmbeddingService(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]: pass

    @abstractmethod
    async def embed_texts_batch(self, texts: List[str]) -> List[List[float]]: pass