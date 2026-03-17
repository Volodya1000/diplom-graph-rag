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
        known_entities: str = "",
    ) -> ExtractionResult:
        """
        Извлекает сущности и тройки из текста.

        Args:
            text: текст чанка
            tbox_classes: классы онтологии
            tbox_relations: допустимые отношения
            known_entities: уже известные сущности из предыдущих чанков
        """
        ...