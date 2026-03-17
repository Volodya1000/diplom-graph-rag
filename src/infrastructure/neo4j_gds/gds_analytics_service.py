"""
Neo4j GDS — community detection, PPR, сводки.

Исправление: проекция с orientation='UNDIRECTED' для Leiden/Louvain.
"""

import logging
from typing import List, Dict, Any

from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.value_objects.graph_community import GraphCommunity
from src.persistence.neo4j.session_manager import Neo4jSessionManager

logger = logging.getLogger(__name__)


class Neo4jGDSAnalyticsService(IGraphAnalyticsService):
    def __init__(self, session_manager: Neo4jSessionManager):
        self._sm = session_manager

    # ============= PROJECTION =============

    async def ensure_projection(
        self, projection_name: str = "instance_graph",
    ) -> None:
        async with self._sm.session() as s:
            res = await s.run(
                "CALL gds.graph.exists($name) YIELD exists",
                {"name": projection_name},
            )
            record = await res.single()
            if record and record["exists"]:
                logger.debug(
                    f"📊 Проекция '{projection_name}' уже существует"
                )
                return

            # UNDIRECTED — обязательно для Leiden/Louvain
            await s.run("""
                CALL gds.graph.project(
                    $name,
                    'Instance',
                    {
                        ALL_RELS: {
                            type: '*',
                            orientation: 'UNDIRECTED'
                        }
                    },
                    {
                        nodeProperties: ['embedding']
                    }
                )
            """, {"name": projection_name})
            logger.info(f"📊 Проекция '{projection_name}' создана (UNDIRECTED)")

    async def drop_projection(
        self, projection_name: str = "instance_graph",
    ) -> None:
        async with self._sm.session() as s:
            res = await s.run(
                "CALL gds.graph.exists($name) YIELD exists",
                {"name": projection_name},
            )
            record = await res.single()
            if record and record["exists"]:
                await s.run(
                    "CALL gds.graph.drop($name)",
                    {"name": projection_name},
                )
                logger.info(f"📊 Проекция '{projection_name}' удалена")

    # ============= COMMUNITY DETECTION =============

    async def detect_communities(
        self,
        algorithm: str = "leiden",
        projection_name: str = "instance_graph",
        write_property: str = "community_id",
    ) -> int:
        await self.ensure_projection(projection_name)

        algo_map = {
            "leiden": "gds.leiden.write",
            "louvain": "gds.louvain.write",
        }
        algo_call = algo_map.get(algorithm)
        if not algo_call:
            raise ValueError(
                f"Неизвестный алгоритм: {algorithm}. "
                f"Доступны: {list(algo_map)}"
            )

        query = f"""
            CALL {algo_call}(
                $projection,
                {{writeProperty: $prop}}
            )
            YIELD communityCount, modularity
            RETURN communityCount, modularity
        """
        async with self._sm.session() as s:
            res = await s.run(query, {
                "projection": projection_name,
                "prop": write_property,
            })
            record = await res.single()

        count = record["communityCount"]
        modularity = record["modularity"]
        logger.info(
            f"🧩 {algorithm}: {count} сообществ, "
            f"modularity={modularity:.4f}"
        )
        return count

    async def get_communities(self) -> List[GraphCommunity]:
        query = """
        MATCH (i:Instance)
        WHERE i.community_id IS NOT NULL
        WITH i.community_id AS cid,
             collect({
                 instance_id: i.instance_id,
                 name: i.name,
                 class_name: i.class_name
             }) AS members
        OPTIONAL MATCH (cs:CommunitySummary {community_id: cid})
        RETURN cid               AS community_id,
               size(members)     AS entity_count,
               [m IN members | m.name][..10] AS key_entities,
               cs.summary        AS summary
        ORDER BY entity_count DESC
        """
        async with self._sm.session() as s:
            res = await s.run(query)
            data = await res.data()

        return [
            GraphCommunity(
                community_id=r["community_id"],
                entity_count=r["entity_count"],
                key_entities=r.get("key_entities", []),
                summary=r.get("summary"),
            )
            for r in data
        ]

    async def get_community_members(
        self, community_id: int,
    ) -> List[Dict[str, Any]]:
        query = """
        MATCH (i:Instance {community_id: $cid})
        OPTIONAL MATCH (i)-[r]->(other:Instance {community_id: $cid})
        WITH i, collect({
            predicate: type(r),
            target: other.name
        }) AS relations
        RETURN i.instance_id AS instance_id,
               i.name        AS name,
               i.class_name  AS class_name,
               relations
        """
        async with self._sm.session() as s:
            res = await s.run(query, {"cid": community_id})
            return await res.data()

    # ============= SUMMARY PERSISTENCE =============

    async def save_community_summary(
        self,
        community_id: int,
        summary: str,
        key_entities: List[str],
    ) -> None:
        async with self._sm.session() as s:
            await s.run("""
                MERGE (cs:CommunitySummary {community_id: $cid})
                SET cs.summary       = $summary,
                    cs.key_entities   = $entities,
                    cs.updated_at     = datetime()
            """, {
                "cid": community_id,
                "summary": summary,
                "entities": key_entities[:20],
            })

    # ============= PPR =============

    async def personalized_pagerank(
        self,
        seed_instance_ids: List[str],
        top_k: int = 20,
        damping_factor: float = 0.85,
        projection_name: str = "instance_graph",
    ) -> List[Dict[str, Any]]:
        await self.ensure_projection(projection_name)

        query = """
        MATCH (seed:Instance)
        WHERE seed.instance_id IN $seed_ids
        WITH collect(seed) AS sourceNodes
        CALL gds.pageRank.stream($projection, {
            sourceNodes: sourceNodes,
            dampingFactor: $damping,
            maxIterations: 20
        })
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS node, score
        WHERE node:Instance
        RETURN node.instance_id AS instance_id,
               node.name        AS name,
               node.class_name  AS class_name,
               node.chunk_id    AS chunk_id,
               score
        ORDER BY score DESC
        LIMIT $top_k
        """
        async with self._sm.session() as s:
            res = await s.run(query, {
                "seed_ids": seed_instance_ids,
                "projection": projection_name,
                "damping": damping_factor,
                "top_k": top_k,
            })
            data = await res.data()

        logger.info(
            f"📈 PPR: {len(seed_instance_ids)} seeds → "
            f"{len(data)} results"
        )
        return data