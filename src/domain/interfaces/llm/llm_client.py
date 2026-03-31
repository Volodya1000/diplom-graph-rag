from abc import ABC, abstractmethod
from typing import List
from src.domain.models.extraction import ExtractionResult
from src.domain.ontology.schema import SchemaClass, SchemaRelation


class ILLMClient(ABC):
    @abstractmethod
    async def extract_entities_and_triples(
        self,
        text: str,
        tbox_classes: List[SchemaClass],
        tbox_relations: List[SchemaRelation],
        known_entities: str = "",
    ) -> ExtractionResult: ...
