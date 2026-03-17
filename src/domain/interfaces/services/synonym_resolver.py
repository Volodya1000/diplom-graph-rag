"""Интерфейс для резолвинга синонимов."""

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
        text_snippets: str = "",
    ) -> SynonymResolutionResult:
        """
        Анализирует сущности и находит синонимы.

        Args:
            instances: все сущности документа
            document_context: краткое описание документа
            text_snippets: фрагменты текста для контекста
        """
        ...