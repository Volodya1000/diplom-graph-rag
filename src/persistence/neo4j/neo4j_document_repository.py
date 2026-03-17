"""Документы и чанки."""

import logging
from typing import List

from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.graph_components.nodes import DocumentNode, ChunkNode
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from src.persistence.neo4j.mappers.node_mappers import (
    map_to_document,
    map_to_chunk,
)

logger = logging.getLogger(__name__)


class Neo4jDocumentRepository(Neo4jBaseRepository, IDocumentRepository):

    async def save_document(self, document: DocumentNode) -> None:
        await self._execute("""
            MERGE (d:Document {doc_id: $doc_id})
            SET d += $props
        """, {
            "doc_id": document.doc_id,
            "props": document.model_dump(exclude={"doc_id"}),
        })

    async def save_chunk(self, chunk: ChunkNode) -> None:
        params = {
            "chunk_id": chunk.chunk_id,
            "props": chunk.model_dump(exclude={"chunk_id", "embedding"}),
        }

        if chunk.embedding is not None:
            query = """
                MERGE (c:Chunk {chunk_id: $chunk_id})
                SET c += $props
                WITH c
                CALL db.create.setNodeVectorProperty(c, 'embedding', $embedding)
            """
            params["embedding"] = chunk.embedding
        else:
            query = """
                MERGE (c:Chunk {chunk_id: $chunk_id})
                SET c += $props
            """

        await self._execute(query, params)

    async def get_document_by_filename(
        self, filename: str,
    ) -> List[DocumentNode]:
        data = await self._fetch_all("""
            MATCH (d:Document {filename: $filename})
            RETURN d.doc_id       AS doc_id,
                   d.filename     AS filename,
                   d.upload_date  AS upload_date
        """, {"filename": filename})
        return [map_to_document(r) for r in data]

    async def get_chunks_by_document(
        self, doc_id: str,
    ) -> List[ChunkNode]:
        data = await self._fetch_all("""
            MATCH (c:Chunk {doc_id: $doc_id})
            RETURN c.chunk_id    AS chunk_id,
                   c.doc_id      AS doc_id,
                   c.chunk_index AS chunk_index,
                   c.text        AS text,
                   c.headings    AS headings,
                   c.start_page  AS start_page,
                   c.end_page    AS end_page,
                   c.embedding   AS embedding
            ORDER BY c.chunk_index
        """, {"doc_id": doc_id})
        return [map_to_chunk(r) for r in data]