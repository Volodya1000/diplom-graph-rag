from abc import ABC, abstractmethod
from typing import List
from src.domain.models import (
    DocumentNode, ChunkNode, SchemaClass, InstanceNode, GraphEdge
)


class IGraphRepository(ABC):
    # === Примитивы сохранения узлов ===
    @abstractmethod
    async def save_document(self, document: DocumentNode) -> None:
        pass

    @abstractmethod
    async def save_chunk(self, chunk: ChunkNode) -> None:
        pass

    @abstractmethod
    async def save_instance(self, instance: InstanceNode) -> None:
        pass

    # === Универсальное сохранение рёбер ===
    @abstractmethod
    async def save_edges(self, edges: List[GraphEdge]) -> None:
        pass

    # === Остальные методы ===
    @abstractmethod
    async def get_tbox_classes(self) -> List[SchemaClass]:
        pass

    @abstractmethod
    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None:
        pass

    @abstractmethod
    async def find_candidates_by_vector(
        self, embedding: List[float], limit: int = 5
    ) -> List[InstanceNode]:
        pass

