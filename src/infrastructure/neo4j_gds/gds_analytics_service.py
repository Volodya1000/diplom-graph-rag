import logging
from typing import List, Dict, Any
from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.value_objects.graph_community import GraphCommunity
from src.persistence.neo4j.base_repository import Neo4jBaseRepository  # ← добавлено
from src.persistence.neo4j.queries.analytics_queries import (
    GraphExistsQuery,
    GraphProjectQuery,
    DropProjectionQuery,
    DetectCommunitiesQuery,
    GetCommunitiesQuery,
    GetCommunityMembersQuery,
    SaveCommunitySummaryQuery,
    PersonalizedPageRankQuery,
)

logger = logging.getLogger(__name__)


class Neo4jGDSAnalyticsService(
    Neo4jBaseRepository, IGraphAnalyticsService
):  # ← наследование
    def __init__(self, session_manager):
        super().__init__(session_manager)

    async def ensure_projection(self, projection_name: str = "instance_graph") -> None:
        exists_query = GraphExistsQuery(name=projection_name)
        data = await self._sm.session().run(
            exists_query.get_query(), exists_query.get_params()
        )
        record = await data.single()
        if record and record["exists"]:
            return
        await self._execute(GraphProjectQuery(name=projection_name))
        logger.info(f"📊 Проекция '{projection_name}' создана (UNDIRECTED)")

    async def drop_projection(self, projection_name: str = "instance_graph") -> None:
        exists_query = GraphExistsQuery(name=projection_name)
        data = await self._sm.session().run(
            exists_query.get_query(), exists_query.get_params()
        )
        record = await data.single()
        if record and record["exists"]:
            await self._execute(DropProjectionQuery(name=projection_name))
            logger.info(f"📊 Проекция '{projection_name}' удалена")

    async def detect_communities(
        self,
        algorithm: str = "leiden",
        projection_name: str = "instance_graph",
        write_property: str = "community_id",
    ) -> int:
        algo_map = {"leiden": "gds.leiden.write", "louvain": "gds.louvain.write"}
        algo_call = algo_map[algorithm]
        query = DetectCommunitiesQuery(
            projection=projection_name, prop=write_property, algo_call=algo_call
        )
        data = await self._fetch_all(query)
        record = data[0]
        count = record["communityCount"]
        logger.info(f"🧩 {algorithm}: {count} сообществ")
        return count

    async def get_communities(self) -> List[GraphCommunity]:
        query = GetCommunitiesQuery()
        data = await self._fetch_all(query)
        return [
            GraphCommunity(
                community_id=r["community_id"],
                entity_count=r["entity_count"],
                key_entities=r.get("key_entities", []),
                summary=r.get("summary"),
            )
            for r in data
        ]

    async def get_community_members(self, community_id: int) -> List[Dict[str, Any]]:
        query = GetCommunityMembersQuery(community_id=community_id)
        return await self._fetch_all(query)

    async def save_community_summary(
        self, community_id: int, summary: str, key_entities: List[str]
    ) -> None:
        query = SaveCommunitySummaryQuery(
            community_id=community_id, summary=summary, key_entities=key_entities
        )
        await self._execute(query)

    async def personalized_pagerank(
        self,
        seed_instance_ids: List[str],
        top_k: int = 20,
        damping_factor: float = 0.85,
        projection_name: str = "instance_graph",
    ) -> List[Dict[str, Any]]:
        query = PersonalizedPageRankQuery(
            seed_ids=seed_instance_ids,
            projection=projection_name,
            damping=damping_factor,
            top_k=top_k,
        )
        return await self._fetch_all(query)
