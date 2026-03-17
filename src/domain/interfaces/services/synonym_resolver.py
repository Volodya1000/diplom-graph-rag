"""Интерфейс для резолвинга синонимов после обработки документа."""

from abc import ABC, abstractmethod
from typing import List

from src.domain.graph_components.nodes import InstanceNode
from src.domain.value_objects.synonym_group import SynonymResolutionResult


class ISynonymResolver(ABC):
    @abstractmethod
    async def find_synonym_groups(
            self,
            instances: List[InstanceNode],
            document_context: str,
    ) -> SynonymResolutionResult:
        """
        Анализирует список сущностей документа и находит синонимы.

        Args:
            instances: все сущности документа
            document_context: краткое описание документа для контекста

        Returns:
            Группы синонимов с каноническими именами
        """
        ...