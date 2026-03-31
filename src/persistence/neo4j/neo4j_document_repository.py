import logging
from typing import List
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.models.nodes import DocumentNode, ChunkNode
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from .queries.document_queries import (
    SaveDocumentQuery,
    SaveChunkQuery,
    GetDocumentByFilenameQuery,
    GetChunksByDocumentQuery,
)

logger = logging.getLogger(__name__)


class Neo4jDocumentRepository(Neo4jBaseRepository, IDocumentRepository):
    def __init__(self, session_manager):
        super().__init__(session_manager)

    async def save_document(self, document: DocumentNode) -> None:
        query = SaveDocumentQuery(
            doc_id=document.doc_id, props=document.model_dump(exclude={"doc_id"})
        )
        await self._execute(query)

    async def save_chunk(self, chunk: ChunkNode) -> None:
        query = SaveChunkQuery(
            chunk_id=chunk.chunk_id,
            props=chunk.model_dump(exclude={"chunk_id", "embedding"}),
            embedding=chunk.embedding if chunk.embedding else None,
        )
        await self._execute(query)

    async def get_document_by_filename(self, filename: str) -> List[DocumentNode]:
        return await self._fetch_all(GetDocumentByFilenameQuery(filename=filename))

    async def get_chunks_by_document(self, doc_id: str) -> List[ChunkNode]:
        return await self._fetch_all(GetChunksByDocumentQuery(doc_id=doc_id))
