"""Генерация финального ответа по контексту."""

from abc import ABC, abstractmethod


class IAnswerGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        question: str,
        context: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        Генерирует ответ на вопрос по предоставленному контексту.

        Args:
            question: вопрос пользователя
            context: собранный контекст (чанки + тройки + summaries)
            system_prompt: опциональный системный промпт

        """
        ...
