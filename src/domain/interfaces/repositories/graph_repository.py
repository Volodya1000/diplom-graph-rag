from abc import ABC, abstractmethod
from typing import List
from src.domain.models import DocumentNode, ChunkNode, SchemaClass, InstanceNode

class IGraphRepository(ABC):
    @abstractmethod
    async def save_document_and_chunks(self, document: DocumentNode, chunks: List[ChunkNode]) -> None: pass

    @abstractmethod
    async def get_tbox_classes(self) -> List[SchemaClass]: pass

    @abstractmethod
    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None: pass

    @abstractmethod
    async def find_candidates_by_vector(self, embedding: List[float], limit: int = 5) -> List[InstanceNode]: pass

    @abstractmethod
    async def save_instances(self, instances: List[InstanceNode]) -> None: pass