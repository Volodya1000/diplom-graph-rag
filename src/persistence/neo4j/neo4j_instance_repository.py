"""Экземпляры сущностей, vector search, семантические связи."""

import re
import logging
from typing import List

from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.graph_components.nodes import InstanceNode
from src.application.dtos.extraction_dtos import ResolvedTriple
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from src.persistence.neo4j.mappers.node_mappers import (
    map_to_instance,
    map_to_triple_dict,
)

logger = logging.getLogger(__name__)

_SAFE_REL = re.compile(r"[^A-Za-z0-9_]")


class Neo4jInstanceRepository(Neo4jBaseRepository, IInstanceRepository):

    async def save_instance(self, instance: InstanceNode) -> None:
        params = {
            "instance_id": instance.instance_id,
            "props": instance.model_dump(exclude={"instance_id", "embedding"}),
        }

        if instance.embedding is not None:
            query = """
                MERGE (i:Instance {instance_id: $instance_id})
                SET i += $props
                WITH i
                CALL db.create.setNodeVectorProperty(i, 'embedding', $embedding)
            """
            params["embedding"] = instance.embedding
        else:
            query = """
                MERGE (i:Instance {instance_id: $instance_id})
                SET i += $props
            """

        await self._execute(query, params)

    # ==================== СЕМАНТИЧЕСКИЕ СВЯЗИ ====================

    async def save_instance_relation(self, triple: ResolvedTriple) -> None:
        safe_name = _SAFE_REL.sub("_", triple.relation_name).upper()
        if not safe_name:
            safe_name = "RELATED_TO"

        # relation_name — из перечисленных в T-Box или нормализованных
        # предикатов, инъекция невозможна (sanitized выше)
        query = f"""
            MATCH (src:Instance {{instance_id: $source_id}})
            MATCH (tgt:Instance {{instance_id: $target_id}})
            MERGE (src)-[r:{safe_name}]->(tgt)
            SET r.chunk_id = $chunk_id
        """
        await self._execute(query, {
            "source_id": triple.source_instance_id,
            "target_id": triple.target_instance_id,
            "chunk_id": triple.chunk_id,
        })

    # ==================== VECTOR SEARCH ====================

    async def find_candidates_by_vector(
        self, embedding: List[float], limit: int = 10,
    ) -> List[InstanceNode]:
        threshold = self._settings.vector_search_threshold
        try:
            data = await self._fetch_all("""
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
            """, {
                "embedding": embedding,
                "limit": limit,
                "threshold": threshold,
            })

            candidates = [map_to_instance(r) for r in data]

            if candidates:
                logger.debug(
                    f"🔎 Vector search: {len(candidates)} candidates "
                    f"(top: «{candidates[0].name}» "
                    f"score={data[0]['score']:.3f})"
                )
            return candidates

        except Exception as e:
            logger.warning(
                f"⚠️ Vector search недоступен: "
                f"{e.__class__.__name__}: {e}"
            )
            return []

    # ==================== ЧТЕНИЕ ====================

    async def get_instances_by_chunk(
        self, chunk_id: str,
    ) -> List[InstanceNode]:
        data = await self._fetch_all("""
            MATCH (i:Instance)-[:MENTIONED_IN]->(c:Chunk {chunk_id: $chunk_id})
            RETURN i.instance_id AS instance_id,
                   i.name        AS name,
                   i.class_name  AS class_name,
                   i.chunk_id    AS chunk_id,
                   i.embedding   AS embedding
        """, {"chunk_id": chunk_id})
        return [map_to_instance(r) for r in data]

    async def get_triples_by_chunk(self, chunk_id: str) -> List[dict]:
        data = await self._fetch_all("""
            MATCH (src:Instance)-[r]->(tgt:Instance)
            WHERE r.chunk_id = $chunk_id
            RETURN src.name       AS subject_name,
                   src.class_name AS subject_type,
                   type(r)        AS predicate,
                   tgt.name       AS object_name,
                   tgt.class_name AS object_type
        """, {"chunk_id": chunk_id})
        return [map_to_triple_dict(r) for r in data]

    async def get_instances_by_document(
            self, doc_id: str,
    ) -> List[InstanceNode]:
        data = await self._fetch_all("""
               MATCH (c:Chunk {doc_id: $doc_id})
               MATCH (i:Instance)-[:MENTIONED_IN]->(c)
               RETURN DISTINCT
                      i.instance_id AS instance_id,
                      i.name        AS name,
                      i.class_name  AS class_name,
                      i.chunk_id    AS chunk_id,
                      i.aliases     AS aliases,
                      i.embedding   AS embedding
           """, {"doc_id": doc_id})
        return [map_to_instance(r) for r in data]

    async def merge_instances(
            self,
            canonical_id: str,
            canonical_name: str,
            alias_ids: List[str],
            aliases: List[str],
    ) -> None:
        """
        Мержит alias-ноды в каноническую:
        1. Переносит входящие рёбра alias → canonical
        2. Переносит исходящие рёбра alias → canonical
        3. Обновляет canonical.aliases
        4. Удаляет alias-ноды
        """
        if not alias_ids:
            return

        async with self._sm.session() as s:
            # 1. Переносим входящие рёбра
            await s.run("""
                   UNWIND $alias_ids AS aid
                   MATCH (alias:Instance {instance_id: aid})<-[r]-(source)
                   WHERE source.instance_id <> $canonical_id
                   WITH source, alias, r, type(r) AS rel_type, properties(r) AS props
                   MATCH (canonical:Instance {instance_id: $canonical_id})
                   CALL apoc.create.relationship(source, rel_type, props, canonical) 
                   YIELD rel
                   DELETE r
               """, {
                "alias_ids": alias_ids,
                "canonical_id": canonical_id,
            })

            # 2. Переносим исходящие рёбра
            await s.run("""
                   UNWIND $alias_ids AS aid
                   MATCH (alias:Instance {instance_id: aid})-[r]->(target)
                   WHERE target.instance_id <> $canonical_id
                   WITH alias, target, r, type(r) AS rel_type, properties(r) AS props
                   MATCH (canonical:Instance {instance_id: $canonical_id})
                   CALL apoc.create.relationship(canonical, rel_type, props, target)
                   YIELD rel
                   DELETE r
               """, {
                "alias_ids": alias_ids,
                "canonical_id": canonical_id,
            })

            # 3. Переносим MENTIONED_IN
            await s.run("""
                   UNWIND $alias_ids AS aid
                   MATCH (alias:Instance {instance_id: aid})-[r:MENTIONED_IN]->(c:Chunk)
                   MATCH (canonical:Instance {instance_id: $canonical_id})
                   MERGE (canonical)-[:MENTIONED_IN]->(c)
                   DELETE r
               """, {
                "alias_ids": alias_ids,
                "canonical_id": canonical_id,
            })

            # 4. Обновляем каноническую ноду
            await s.run("""
                   MATCH (c:Instance {instance_id: $canonical_id})
                   SET c.name = $canonical_name,
                       c.aliases = $aliases
               """, {
                "canonical_id": canonical_id,
                "canonical_name": canonical_name,
                "aliases": aliases,
            })

            # 5. Удаляем alias-ноды
            await s.run("""
                   UNWIND $alias_ids AS aid
                   MATCH (alias:Instance {instance_id: aid})
                   DETACH DELETE alias
               """, {"alias_ids": alias_ids})

        logger.info(
            f"🔗 Merged {len(alias_ids)} aliases → "
            f"«{canonical_name}» ({canonical_id[:8]}…)"
        )

    async def get_all_instances(self) -> List[InstanceNode]:
        data = await self._fetch_all("""
               MATCH (i:Instance)
               RETURN i.instance_id AS instance_id,
                      i.name        AS name,
                      i.class_name  AS class_name,
                      i.chunk_id    AS chunk_id,
                      i.aliases     AS aliases,
                      i.embedding   AS embedding
           """)
        return [map_to_instance(r) for r in data]