from abc import ABC, abstractmethod
from typing import List
from src.domain.models.search import RetrievalResult


class IRetrievalStrategy(ABC):
    @abstractmethod
    async def retrieve(
        self, query: str, query_embedding: List[float], top_k: int = 10
    ) -> RetrievalResult: ...
    @property
    @abstractmethod
    def name(self) -> str: ...
