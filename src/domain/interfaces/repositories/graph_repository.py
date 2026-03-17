from abc import ABC, abstractmethod
from typing import List
from src.domain.models import (
    DocumentNode,
    ChunkNode,
    SchemaClass,
    InstanceNode,
    GraphEdge
)


class IGraphRepository(ABC):

    # ==================== НОВЫЕ ПРИМИТИВНЫЕ МЕТОДЫ (рекомендуется) ====================
    @abstractmethod
    async def save_document(self, document: DocumentNode) -> None:
        pass

    @abstractmethod
    async def save_chunk(self, chunk: ChunkNode) -> None:
        pass

    @abstractmethod
    async def save_edges(self, edges: List[GraphEdge]) -> None:
        pass

    # ==================== СТАРЫЙ МЕТОД (оставлен как обёртка для совместимости) ====================
    @abstractmethod
    async def save_document_and_chunks(
        self, document: DocumentNode, chunks: List[ChunkNode]
    ) -> None:
        """Deprecated. Используй save_document + save_chunk + save_edges"""
        pass

    # ==================== Остальные методы без изменений ====================
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

    @abstractmethod
    async def save_instances(self, instances: List[InstanceNode]) -> None:
        pass