import logging

from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.models.nodes import ChunkNode, DocumentNode, DocumentStats
from src.persistence.neo4j.base_repository import Neo4jBaseRepository

from .queries.document_queries import (
    GetChunksByDocumentQuery,
    GetDocumentByFilenameQuery,
    SaveChunkQuery,
    SaveDocumentQuery,
    GetDocumentStatsQuery,
    GetAllDocumentsStatsQuery,
)

logger = logging.getLogger(__name__)


class Neo4jDocumentRepository(Neo4jBaseRepository, IDocumentRepository):
    def __init__(self, session_manager):
        super().__init__(session_manager)

    async def save_document(self, document: DocumentNode) -> None:
        query = SaveDocumentQuery(
            doc_id=document.doc_id,
            props=document.model_dump(exclude={"doc_id"}),
        )
        await self._execute(query)

    async def save_chunk(self, chunk: ChunkNode) -> None:
        query = SaveChunkQuery(
            chunk_id=chunk.chunk_id,
            props=chunk.model_dump(exclude={"chunk_id", "embedding"}),
            embedding=chunk.embedding or None,
        )
        await self._execute(query)

    async def get_document_by_filename(self, filename: str) -> list[DocumentNode]:
        return await self._fetch_all(GetDocumentByFilenameQuery(filename=filename))

    async def get_chunks_by_document(self, doc_id: str) -> list[ChunkNode]:
        return await self._fetch_all(GetChunksByDocumentQuery(doc_id=doc_id))

    async def get_all_documents_with_stats(self) -> list[DocumentStats]:
        return await self._fetch_all(GetAllDocumentsStatsQuery())

    async def get_document_stats(self, doc_id: str) -> DocumentStats | None:
        results = await self._fetch_all(GetDocumentStatsQuery(doc_id=doc_id))
        return results[0] if results else None
