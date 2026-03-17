"""Генерация финального ответа по контексту."""

from abc import ABC, abstractmethod
from typing import Optional


class IAnswerGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        question: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Генерирует ответ на вопрос по предоставленному контексту.

        Args:
            question: вопрос пользователя
            context: собранный контекст (чанки + тройки + summaries)
            system_prompt: опциональный системный промпт
        """
        ...