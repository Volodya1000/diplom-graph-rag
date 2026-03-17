from abc import ABC, abstractmethod
from typing import List
from src.domain.models import SchemaClass, RawExtractedEntity

class ILLMClient(ABC):
    @abstractmethod
    async def extract_entities(self, text: str, tbox_schema: List[SchemaClass]) -> List[RawExtractedEntity]: pass