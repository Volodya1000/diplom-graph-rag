from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

# Определяем дженерик для возвращаемого типа Pydantic
T = TypeVar("T", bound=BaseModel)


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

    @abstractmethod
    async def generate_structured(
        self,
        question: str,
        context: str,
        output_model: Type[T],
        system_prompt: str | None = None,
    ) -> T:
        """Генерирует строго типизированный ответ на основе Pydantic-модели."""
