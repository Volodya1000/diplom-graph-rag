"""
Стратегия извлечения контекста — ключевой интерфейс RAG.

Каждая стратегия получает вопрос + эмбеддинг и возвращает
RetrievalResult. Стратегии компонуются (Hybrid = Local + Global).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.value_objects.search_context import RetrievalResult


class IRetrievalStrategy(ABC):
    """Единый контракт для всех стратегий поиска."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> RetrievalResult:
        """
        Извлечь релевантный контекст для ответа на вопрос.

        Args:
            query: текст вопроса (для LLM-reranking, если нужно)
            query_embedding: вектор вопроса
            top_k: максимум результатов

        Returns:
            RetrievalResult с чанками, тройками, сообществами
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя стратегии (для логов и выбора)."""
        ...