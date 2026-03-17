from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field

from src.application.dtos.extraction_dtos import RawExtractedEntity, RawExtractedTriple
from src.domain.ontology.shema import SchemaClass, SchemaRelation

class ExtractionResult(BaseModel):
    entities: List[RawExtractedEntity] = Field(default_factory=list)
    triples: List[RawExtractedTriple] = Field(default_factory=list)

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


