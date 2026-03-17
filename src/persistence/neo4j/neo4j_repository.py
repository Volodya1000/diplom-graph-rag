from neo4j import AsyncGraphDatabase
from typing import List
import logging
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.models import DocumentNode, ChunkNode, SchemaClass, InstanceNode

logger = logging.getLogger(__name__)


class Neo4jRepository(IGraphRepository):
    def __init__(self, uri, user, password):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def save_document_and_chunks(
        self,
        document: DocumentNode,
        chunks: List[ChunkNode]
    ) -> None:
        if not chunks:
            logger.warning("Пустой список чанков — сохранять нечего")
            return

        # ВАЖНО: сортируем заранее, чтобы порядок был детерминированный
        chunks_sorted = sorted(chunks, key=lambda c: c.chunk_index)

        query = """
        MERGE (d:Document {doc_id: $doc.doc_id})
        SET d.filename = $doc.filename,
            d.upload_date = $doc.upload_date

        WITH d
        UNWIND $chunks AS ch

        MERGE (c:Chunk {chunk_id: ch.chunk_id})
        SET c.doc_id = ch.doc_id,
            c.chunk_index = ch.chunk_index,
            c.text = ch.text,
            c.start_page = ch.start_page,
            c.end_page = ch.end_page

        WITH d, c, ch
        CALL db.create.setNodeVectorProperty(c, 'embedding', ch.embedding)

        MERGE (d)-[:HAS_CHUNK]->(c)

        WITH $chunks AS chunks
        // строим связи ТОЛЬКО по входному порядку (никаких MATCH обратно)
        UNWIND range(0, size(chunks) - 2) AS i

        WITH chunks[i] AS ch1, chunks[i+1] AS ch2

        MATCH (c1:Chunk {chunk_id: ch1.chunk_id})
        MATCH (c2:Chunk {chunk_id: ch2.chunk_id})

        // защита от самоссылок (на всякий случай)
        WHERE c1.chunk_id <> c2.chunk_id

        MERGE (c1)-[:NEXT_CHUNK]->(c2)
        MERGE (c2)-[:PREV_CHUNK]->(c1)
        """

        params = {
            "doc": document.model_dump(),
            "chunks": [c.model_dump() for c in chunks_sorted],
        }

        async with self.driver.session() as session:
            await session.run(query, params)

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
        # MVP-заглушка
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