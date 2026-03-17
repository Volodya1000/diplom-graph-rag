from abc import ABC, abstractmethod
from typing import List

from src.domain.graph_components.nodes import DocumentNode, ChunkNode


class IDocumentRepository(ABC):
    """Документы и их чанки."""

    @abstractmethod
    async def save_document(self, document: DocumentNode) -> None: ...

    @abstractmethod
    async def save_chunk(self, chunk: ChunkNode) -> None: ...

    @abstractmethod
    async def get_document_by_filename(
        self, filename: str,
    ) -> List[DocumentNode]: ...

    @abstractmethod
    async def get_chunks_by_document(
        self, doc_id: str,
    ) -> List[ChunkNode]: ...