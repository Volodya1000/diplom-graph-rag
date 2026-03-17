from neo4j import AsyncGraphDatabase
from typing import List
import logging

from src.config.neo4j_settings import Neo4jSettings
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.models import (
    DocumentNode, ChunkNode, SchemaClass, InstanceNode, GraphEdge
)

logger = logging.getLogger(__name__)


class Neo4jRepository(IGraphRepository):
    def __init__(self, settings: Neo4jSettings):
        self._settings = settings
        self.driver = AsyncGraphDatabase.driver(
            settings.uri,
            auth=(settings.user, settings.password_value),
        )

    # ====================== ПРИМИТИВЫ УЗЛОВ ======================
    async def save_document(self, document: DocumentNode) -> None:
        query = """
        MERGE (d:Document {doc_id: $doc_id})
        SET d += $props
        """
        params = {
            "doc_id": document.doc_id,
            "props": document.model_dump(exclude={"doc_id"}),
        }
        async with self.driver.session() as session:
            await session.run(query, params)

    async def save_chunk(self, chunk: ChunkNode) -> None:
        query = """
        MERGE (c:Chunk {chunk_id: $chunk_id})
        SET c += $props
        """
        params = {
            "chunk_id": chunk.chunk_id,
            "props": chunk.model_dump(exclude={"chunk_id", "embedding"}),
        }

        if chunk.embedding is not None:
            query += """
            WITH c
            CALL db.create.setNodeVectorProperty(c, 'embedding', $embedding)
            """
            params["embedding"] = chunk.embedding

        async with self.driver.session() as session:
            await session.run(query, params)

    async def save_instance(self, instance: InstanceNode) -> None:
        query = """
        MERGE (i:Instance {instance_id: $instance_id})
        SET i += $props
        """
        params = {
            "instance_id": instance.instance_id,
            "props": instance.model_dump(exclude={"instance_id", "embedding"}),
        }

        if instance.embedding is not None:
            query += """
            WITH i
            CALL db.create.setNodeVectorProperty(i, 'embedding', $embedding)
            """
            params["embedding"] = instance.embedding

        async with self.driver.session() as session:
            await session.run(query, params)

    # ====================== УНИВЕРСАЛЬНЫЕ РЁБРА ======================
    async def save_edges(self, edges: List[GraphEdge]) -> None:
        if not edges:
            return
        async with self.driver.session() as session:
            for edge in edges:
                rel_type = edge.relation_type.value
                query = f"""
                MATCH (source)
                WHERE (source:Document  AND source.doc_id      = $source_id)
                   OR (source:Chunk     AND source.chunk_id    = $source_id)
                   OR (source:Instance  AND source.instance_id = $source_id)
                MATCH (target)
                WHERE (target:Chunk       AND target.chunk_id = $target_id)
                   OR (target:SchemaClass AND target.name     = $target_id)
                MERGE (source)-[r:{rel_type}]->(target)
                """
                params = {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                }
                await session.run(query, params)

    # ====================== T-BOX ======================
    async def get_tbox_classes(self) -> List[SchemaClass]:
        query = """
        MATCH (c:SchemaClass)
        RETURN c.name AS name,
               c.status AS status,
               coalesce(c.description, '') AS description
        """
        async with self.driver.session() as session:
            res = await session.run(query)
            data = await res.data()
            return [
                SchemaClass(
                    name=r["name"],
                    status=r["status"],
                    description=r["description"],
                )
                for r in data
            ]

    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None:
        if not classes:
            return
        query = """
        UNWIND $batch AS row
        MERGE (c:SchemaClass {name: row.name})
        ON CREATE SET c.status      = row.status,
                      c.description = row.description
        ON MATCH  SET c.description = row.description
        """
        batch = [
            {
                "name": c.name,
                "status": c.status.value,
                "description": c.description,
            }
            for c in classes
        ]
        async with self.driver.session() as session:
            await session.run(query, batch=batch)

    async def find_candidates_by_vector(
        self, embedding: List[float], limit: int = 5
    ) -> List[InstanceNode]:
        return []