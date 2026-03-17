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