from abc import ABC, abstractmethod
from typing import List

from src.domain.models import SchemaClass, SchemaRelation, ExtractionResult


class ILLMClient(ABC):
    @abstractmethod
    async def extract_entities_and_triples(
        self,
        text: str,
        tbox_classes: List[SchemaClass],
        tbox_relations: List[SchemaRelation],
    ) -> ExtractionResult:
        """
        Извлекает сущности и тройки (subject-predicate-object) из текста
        в рамках ограничений онтологии.
        """
        ...