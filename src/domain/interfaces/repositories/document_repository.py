from abc import ABC, abstractmethod

from src.domain.models.nodes import ChunkNode, DocumentNode


class IDocumentRepository(ABC):
    @abstractmethod
    async def save_document(self, document: DocumentNode) -> None: ...
    @abstractmethod
    async def save_chunk(self, chunk: ChunkNode) -> None: ...
    @abstractmethod
    async def get_document_by_filename(self, filename: str) -> list[DocumentNode]: ...
    @abstractmethod
    async def get_chunks_by_document(self, doc_id: str) -> list[ChunkNode]: ...
