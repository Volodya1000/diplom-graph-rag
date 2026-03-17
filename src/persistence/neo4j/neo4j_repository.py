"""
Neo4j-реализация IGraphRepository.

Включает:
  - Векторные индексы для Instance и Chunk
  - Поиск кандидатов по cosine similarity
  - SUBCLASS_OF, ALLOWED_RELATION, динамические рёбра
"""

import re
import logging
from typing import List

from neo4j import AsyncGraphDatabase
from neo4j.time import DateTime as Neo4jDateTime


from src.config.neo4j_settings import Neo4jSettings
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from domain.graph_components.edges import GraphEdge
from application.dtos.extraction_dtos import ResolvedTriple
from domain.ontology.shema import SchemaClass, SchemaRelation
from domain.graph_components.nodes import DocumentNode, ChunkNode, InstanceNode

logger = logging.getLogger(__name__)

_SAFE_REL = re.compile(r"[^A-Za-z0-9_]")


class Neo4jRepository(IGraphRepository):
    def __init__(self, settings: Neo4jSettings):
        self._settings = settings
        self.driver = AsyncGraphDatabase.driver(
            settings.uri,
            auth=(settings.user, settings.password_value),
        )

    # ====================== ИНДЕКСЫ ======================

    async def ensure_indexes(self) -> None:
        """Создаёт векторные индексы IF NOT EXISTS."""
        dim = self._settings.embedding_dim
        async with self.driver.session() as s:
            # Индекс на эмбеддинги экземпляров (для Entity Resolution)
            await s.run(f"""
                CREATE VECTOR INDEX instance_embedding IF NOT EXISTS
                FOR (n:Instance) ON (n.embedding)
                OPTIONS {{indexConfig: {{
                  `vector.dimensions`: {dim},
                  `vector.similarity_function`: 'cosine'
                }}}}
            """)
            # Индекс на эмбеддинги чанков (для RAG-поиска)
            await s.run(f"""
                CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
                FOR (c:Chunk) ON (c.embedding)
                OPTIONS {{indexConfig: {{
                  `vector.dimensions`: {dim},
                  `vector.similarity_function`: 'cosine'
                }}}}
            """)
            # Текстовые индексы для быстрого lookup
            await s.run("""
                CREATE INDEX instance_name_idx IF NOT EXISTS
                FOR (i:Instance) ON (i.name)
            """)
            await s.run("""
                CREATE INDEX schema_class_name_idx IF NOT EXISTS
                FOR (c:SchemaClass) ON (c.name)
            """)
        logger.info(f"📐 Индексы обеспечены (embedding_dim={dim})")

    # ====================== УЗЛЫ ======================

    async def save_document(self, document: DocumentNode) -> None:
        query = """
        MERGE (d:Document {doc_id: $doc_id})
        SET d += $props
        """
        params = {
            "doc_id": document.doc_id,
            "props": document.model_dump(exclude={"doc_id"}),
        }
        async with self.driver.session() as s:
            await s.run(query, params)

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

        async with self.driver.session() as s:
            await s.run(query, params)

    async def save_instance(self, instance: InstanceNode) -> None:
        query = """
        MERGE (i:Instance {instance_id: $instance_id})
        SET i += $props
        """
        params = {
            "instance_id": instance.instance_id,
            "props": instance.model_dump(
                exclude={"instance_id", "embedding"},
            ),
        }
        if instance.embedding is not None:
            query += """
            WITH i
            CALL db.create.setNodeVectorProperty(i, 'embedding', $embedding)
            """
            params["embedding"] = instance.embedding

        async with self.driver.session() as s:
            await s.run(query, params)

    # ====================== СТРУКТУРНЫЕ РЁБРА ======================

    async def save_edges(self, edges: List[GraphEdge]) -> None:
        if not edges:
            return
        async with self.driver.session() as s:
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
                await s.run(query, {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                })

    # ====================== T-BOX: КЛАССЫ ======================

    async def get_tbox_classes(self) -> List[SchemaClass]:
        query = """
        MATCH (c:SchemaClass)
        RETURN c.name        AS name,
               c.status      AS status,
               c.description AS description,
               c.parent      AS parent
        """
        async with self.driver.session() as s:
            res = await s.run(query)
            data = await res.data()
            return [
                SchemaClass(
                    name=r["name"],
                    status=r["status"],
                    description=r.get("description") or "",
                    parent=r.get("parent"),
                )
                for r in data
            ]

    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None:
        if not classes:
            return

        batch = [
            {
                "name": c.name,
                "status": c.status.value,
                "description": c.description,
                "parent": c.parent,
            }
            for c in classes
        ]

        async with self.driver.session() as s:
            await s.run(
                """
                UNWIND $batch AS row
                MERGE (c:SchemaClass {name: row.name})
                ON CREATE SET c.status      = row.status,
                              c.description = row.description,
                              c.parent      = row.parent
                ON MATCH  SET c.description = row.description,
                              c.parent      = row.parent
                """,
                batch=batch,
            )
            await s.run(
                """
                UNWIND $batch AS row
                WITH row WHERE row.parent IS NOT NULL
                MATCH (child:SchemaClass  {name: row.name})
                MATCH (parent:SchemaClass {name: row.parent})
                MERGE (child)-[:SUBCLASS_OF]->(parent)
                """,
                batch=batch,
            )
            await s.run(
                """
                MATCH (child:SchemaClass)
                WHERE child.parent IS NOT NULL
                  AND NOT (child)-[:SUBCLASS_OF]->()
                MATCH (parent:SchemaClass {name: child.parent})
                MERGE (child)-[:SUBCLASS_OF]->(parent)
                """
            )

    # ====================== T-BOX: ОТНОШЕНИЯ ======================

    async def get_schema_relations(self) -> List[SchemaRelation]:
        query = """
        MATCH (src:SchemaClass)-[r:ALLOWED_RELATION]->(tgt:SchemaClass)
        RETURN src.name      AS source_class,
               r.name        AS relation_name,
               tgt.name      AS target_class,
               r.status      AS status,
               r.description AS description
        """
        async with self.driver.session() as s:
            res = await s.run(query)
            data = await res.data()
            return [
                SchemaRelation(
                    source_class=r["source_class"],
                    relation_name=r["relation_name"],
                    target_class=r["target_class"],
                    status=r.get("status", "draft"),
                    description=r.get("description") or "",
                )
                for r in data
            ]

    async def save_schema_relations(
        self, relations: List[SchemaRelation],
    ) -> None:
        if not relations:
            return
        batch = [
            {
                "source_class": r.source_class,
                "relation_name": r.relation_name,
                "target_class": r.target_class,
                "status": r.status.value,
                "description": r.description,
            }
            for r in relations
        ]
        query = """
        UNWIND $batch AS row
        MATCH (src:SchemaClass {name: row.source_class})
        MATCH (tgt:SchemaClass {name: row.target_class})
        MERGE (src)-[r:ALLOWED_RELATION {name: row.relation_name}]->(tgt)
        ON CREATE SET r.status      = row.status,
                      r.description = row.description
        ON MATCH  SET r.description = row.description
        """
        async with self.driver.session() as s:
            await s.run(query, batch=batch)

    # ====================== СЕМАНТИЧЕСКИЕ СВЯЗИ ======================

    async def save_instance_relation(self, triple: ResolvedTriple) -> None:
        safe_name = _SAFE_REL.sub("_", triple.relation_name).upper()
        if not safe_name:
            safe_name = "RELATED_TO"

        query = f"""
        MATCH (src:Instance {{instance_id: $source_id}})
        MATCH (tgt:Instance {{instance_id: $target_id}})
        MERGE (src)-[r:{safe_name}]->(tgt)
        SET r.chunk_id = $chunk_id
        """
        async with self.driver.session() as s:
            await s.run(query, {
                "source_id": triple.source_instance_id,
                "target_id": triple.target_instance_id,
                "chunk_id": triple.chunk_id,
            })

    # ====================== VECTOR SEARCH ======================

    async def find_candidates_by_vector(
        self, embedding: List[float], limit: int = 10,
    ) -> List[InstanceNode]:
        """
        Поиск ближайших Instance-нод по косинусному сходству.
        Использует векторный индекс Neo4j.
        """
        threshold = self._settings.vector_search_threshold
        query = """
        CALL db.index.vector.queryNodes(
            'instance_embedding', $limit, $embedding
        )
        YIELD node AS n, score
        WHERE score >= $threshold
        RETURN n.instance_id AS instance_id,
               n.name        AS name,
               n.class_name  AS class_name,
               n.chunk_id    AS chunk_id,
               score
        ORDER BY score DESC
        """
        try:
            async with self.driver.session() as s:
                result = await s.run(query, {
                    "embedding": embedding,
                    "limit": limit,
                    "threshold": threshold,
                })
                data = await result.data()

            candidates = [
                InstanceNode(
                    instance_id=r["instance_id"],
                    name=r["name"],
                    class_name=r["class_name"],
                    chunk_id=r["chunk_id"],
                )
                for r in data
            ]

            if candidates:
                logger.debug(
                    f"🔎 Vector search: {len(candidates)} candidates "
                    f"(top: «{candidates[0].name}» "
                    f"score={data[0]['score']:.3f})"
                )

            return candidates

        except Exception as e:
            # Индекс ещё не создан или не заполнен
            logger.warning(
                f"⚠️ Vector search недоступен: {e.__class__.__name__}: {e}"
            )
            return []

    async def get_chunks_by_document(self, doc_id: str) -> List[ChunkNode]:
        query = """
           MATCH (c:Chunk {doc_id: $doc_id})
           RETURN c.chunk_id AS chunk_id,
                  c.doc_id AS doc_id,
                  c.chunk_index AS chunk_index,
                  c.text AS text,
                  c.headings AS headings,
                  c.start_page AS start_page,
                  c.end_page AS end_page,
                  c.embedding AS embedding
           ORDER BY c.chunk_index
           """
        async with self.driver.session() as s:
            res = await s.run(query, {"doc_id": doc_id})
            data = await res.data()
            return [
                ChunkNode(
                    chunk_id=r["chunk_id"],
                    doc_id=r["doc_id"],
                    chunk_index=r["chunk_index"],
                    text=r["text"],
                    headings=r.get("headings", []),
                    start_page=r.get("start_page", 0),
                    end_page=r.get("end_page", 0),
                    embedding=r.get("embedding"),
                )
                for r in data
            ]

    async def get_instances_by_chunk(self, chunk_id: str) -> List[InstanceNode]:
        query = """
           MATCH (i:Instance)-[:MENTIONED_IN]->(c:Chunk {chunk_id: $chunk_id})
           RETURN i.instance_id AS instance_id,
                  i.name AS name,
                  i.class_name AS class_name,
                  i.chunk_id AS chunk_id,
                  i.embedding AS embedding
           """
        async with self.driver.session() as s:
            res = await s.run(query, {"chunk_id": chunk_id})
            data = await res.data()
            return [
                InstanceNode(
                    instance_id=r["instance_id"],
                    name=r["name"],
                    class_name=r["class_name"],
                    chunk_id=r["chunk_id"],
                    embedding=r.get("embedding"),
                )
                for r in data
            ]

    async def get_triples_by_chunk(self, chunk_id: str) -> List[dict]:
        query = """
           MATCH (src:Instance)-[r]->(tgt:Instance)
           WHERE r.chunk_id = $chunk_id
           RETURN src.name AS subject_name,
                  src.class_name AS subject_type,
                  type(r) AS predicate,
                  tgt.name AS object_name,
                  tgt.class_name AS object_type
           """
        async with self.driver.session() as s:
            res = await s.run(query, {"chunk_id": chunk_id})
            data = await res.data()
            return [
                {
                    "subject_name": r["subject_name"],
                    "subject_type": r["subject_type"],
                    "predicate": r["predicate"],
                    "object_name": r["object_name"],
                    "object_type": r["object_type"],
                }
                for r in data
            ]

    async def get_document_by_filename(self, filename: str) -> List[DocumentNode]:
        query = """
        MATCH (d:Document {filename: $filename})
        RETURN d.doc_id AS doc_id,
               d.filename AS filename,
               d.upload_date AS upload_date
        """
        async with self.driver.session() as s:
            res = await s.run(query, {"filename": filename})
            data = await res.data()
            result = []
            for r in data:
                upload_date = r["upload_date"]
                # Преобразуем neo4j.time.DateTime в datetime.datetime
                if isinstance(upload_date, Neo4jDateTime):
                    upload_date = upload_date.to_native()
                result.append(
                    DocumentNode(
                        doc_id=r["doc_id"],
                        filename=r["filename"],
                        upload_date=upload_date,
                    )
                )
            return result