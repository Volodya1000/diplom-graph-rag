from neo4j import AsyncGraphDatabase
from typing import List
import logging
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.models import DocumentNode, ChunkNode, SchemaClass, InstanceNode

logger = logging.getLogger(__name__)

class Neo4jRepository(IGraphRepository):
    def __init__(self, uri, user, password):
        logger.info(f"Подключение к Neo4j: {uri}, пользователь: {user}")
        # Проверяем, что пароль не пустой
        if not password:
            logger.error("Пароль Neo4j пустой!")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def save_document_and_chunks(self, document: DocumentNode, chunks: List[ChunkNode]) -> None:
        if not chunks: return
        query = """
        MERGE (d:Document {doc_id: $doc.doc_id})
        SET d.filename = $doc.filename, d.upload_date = $doc.upload_date

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

        WITH d
        MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
        WITH c ORDER BY c.chunk_index ASC
        WITH collect(c) AS ordered_chunks

        // Создаем связи NEXT_CHUNK / PREV_CHUNK только если чанков больше 1
        WITH ordered_chunks WHERE size(ordered_chunks) > 1
        UNWIND range(0, size(ordered_chunks)-2) AS i
        WITH ordered_chunks[i] AS current_chunk, ordered_chunks[i+1] AS next_chunk
        MERGE (current_chunk)-[:NEXT_CHUNK]->(next_chunk)
        MERGE (next_chunk)-[:PREV_CHUNK]->(current_chunk)
        """
        params = {"doc": document.model_dump(), "chunks": [c.model_dump() for c in chunks]}
        async with self.driver.session() as session:
            await session.run(query, params)

    async def get_tbox_classes(self) -> List[SchemaClass]:
        query = "MATCH (c:SchemaClass) RETURN c.name AS name, c.status AS status"
        async with self.driver.session() as session:
            res = await session.run(query)
            return [SchemaClass(**record) for record in await res.data()]

    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None:
        if not classes: return
        query = """
        UNWIND $batch AS row
        MERGE (c:SchemaClass {name: row.name})
        ON CREATE SET c.status = row.status
        """
        batch = [{"name": c.name, "status": c.status.value} for c in classes]
        async with self.driver.session() as session:
            await session.run(query, batch=batch)

    async def find_candidates_by_vector(self, embedding: List[float], limit: int = 5) -> List[InstanceNode]:
        # В MVP можно опустить реальный векторный поиск, если индекс еще не создан
        return []

    async def save_instances(self, instances: List[InstanceNode]) -> None:
        if not instances: return
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