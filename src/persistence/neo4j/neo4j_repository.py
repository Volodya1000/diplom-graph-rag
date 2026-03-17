from neo4j import AsyncGraphDatabase
from typing import List
import logging
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.models import (
    DocumentNode, ChunkNode, SchemaClass, InstanceNode,
    GraphEdge, DocumentAggregate
)

logger = logging.getLogger(__name__)


class Neo4jRepository(IGraphRepository):
    def __init__(self, uri, user, password):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    # ====================== ИСПРАВЛЕННЫЙ save_chunk ======================
    async def save_chunk(self, chunk: ChunkNode) -> None:
        """
        MERGE + SET + (опционально) CALL db.create.setNodeVectorProperty
        Главная ошибка была здесь: после SET нельзя сразу CALL — нужен WITH.
        """
        query = """
        MERGE (c:Chunk {chunk_id: $chunk_id})
        SET c += $props
        """

        params = {
            "chunk_id": chunk.chunk_id,
            "props": chunk.model_dump(exclude={"chunk_id", "embedding"})
        }

        # Добавляем вектор только если он есть
        if chunk.embedding is not None:
            query += """
            WITH c
            CALL db.create.setNodeVectorProperty(c, 'embedding', $embedding)
            """
            params["embedding"] = chunk.embedding

        async with self.driver.session() as session:
            await session.run(query, params)

    # ====================== save_document (без изменений) ======================
    async def save_document(self, document: DocumentNode) -> None:
        query = """
        MERGE (d:Document {doc_id: $doc_id})
        SET d += $props
        """
        params = {
            "doc_id": document.doc_id,
            "props": document.model_dump(exclude={"doc_id"})
        }
        async with self.driver.session() as session:
            await session.run(query, params)

    # ====================== save_edges (без изменений) ======================
    async def save_edges(self, edges: List[GraphEdge]) -> None:
        if not edges:
            return

        async with self.driver.session() as session:
            for edge in edges:
                rel_type = edge.relation_type.value
                query = f"""
                MATCH (source)
                WHERE (source:Document AND source.doc_id = $source_id)
                   OR (source:Chunk    AND source.chunk_id = $source_id)
                MATCH (target)
                WHERE (target:Chunk AND target.chunk_id = $target_id)
                MERGE (source)-[r:{rel_type}]->(target)
                """
                params = {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id
                }
                await session.run(query, params)

    # ====================== Deprecated обёртка ======================
    async def save_document_and_chunks(
        self, document: DocumentNode, chunks: List[ChunkNode]
    ) -> None:
        await self.save_document(document)

        chunks_sorted = sorted(chunks, key=lambda c: c.chunk_index)
        for chunk in chunks_sorted:
            await self.save_chunk(chunk)

        aggregate = DocumentAggregate(document=document, chunks=chunks_sorted)
        edges = aggregate.build_edges()
        await self.save_edges(edges)

    # ====================== Остальные методы (без изменений) ======================
    async def get_tbox_classes(self) -> List[SchemaClass]:
        query = """
        MATCH (c:SchemaClass)
        RETURN c.name AS name, c.status AS status
        """
        async with self.driver.session() as session:
            res = await session.run(query)
            return [SchemaClass(**record) for record in await res.data()]

    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None:
        if not classes:
            return
        query = """
        UNWIND $batch AS row
        MERGE (c:SchemaClass {name: row.name})
        ON CREATE SET c.status = row.status
        """
        batch = [{"name": c.name, "status": c.status.value} for c in classes]
        async with self.driver.session() as session:
            await session.run(query, batch=batch)

    async def find_candidates_by_vector(
        self,
        embedding: List[float],
        limit: int = 5
    ) -> List[InstanceNode]:
        return []

    async def save_instances(self, instances: List[InstanceNode]) -> None:
        if not instances:
            return
        query = """
        UNWIND $batch AS row
        MATCH (class:SchemaClass {name: row.class_name})
        MATCH (chunk:Chunk {chunk_id: row.chunk_id})
        MERGE (inst:Instance {instance_id: row.instance_id})
        SET inst.name = row.name
        MERGE (inst)-[:INSTANCE_OF]->(class)
        MERGE (inst)-[:MENTIONED_IN]->(chunk)
        WITH inst, row
        CALL db.create.setNodeVectorProperty(inst, 'embedding', row.embedding)
        """
        batch = [i.model_dump() for i in instances]
        async with self.driver.session() as session:
            await session.run(query, batch=batch)