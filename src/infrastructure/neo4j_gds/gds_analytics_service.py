import logging
from typing import List, Dict, Any
from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.models.community import GraphCommunity
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
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


class Neo4jGDSAnalyticsService(Neo4jBaseRepository, IGraphAnalyticsService):
    def __init__(self, session_manager):
        super().__init__(session_manager)

    async def ensure_projection(self, projection_name: str = "instance_graph") -> None:
        data = await self._fetch_all(GraphExistsQuery(name=projection_name))
        if data and data[0].get("exists"):
            return
        await self._execute(GraphProjectQuery(name=projection_name))
        logger.info(f"📊 Проекция '{projection_name}' создана (UNDIRECTED)")

    async def drop_projection(self, projection_name: str = "instance_graph") -> None:
        data = await self._fetch_all(GraphExistsQuery(name=projection_name))
        if data and data[0].get("exists"):
            await self._execute(DropProjectionQuery(name=projection_name))
            logger.info(f"📊 Проекция '{projection_name}' удалена")

    async def detect_communities(
        self,
        algorithm: str = "leiden",
        projection_name: str = "instance_graph",
        write_property: str = "community_id",
    ) -> int:
        algo_call = {"leiden": "gds.leiden.write", "louvain": "gds.louvain.write"}[
            algorithm
        ]
        data = await self._fetch_all(
            DetectCommunitiesQuery(
                projection=projection_name, prop=write_property, algo_call=algo_call
            )
        )
        count = data[0]["communityCount"]
        logger.info(f"🧩 {algorithm}: {count} сообществ")
        return count

    async def get_communities(self) -> List[GraphCommunity]:
        return await self._fetch_all(GetCommunitiesQuery())

    async def get_community_members(self, community_id: int) -> List[Dict[str, Any]]:
        return await self._fetch_all(
            GetCommunityMembersQuery(community_id=community_id)
        )

    async def save_community_summary(
        self, community_id: int, summary: str, key_entities: List[str]
    ) -> None:
        await self._execute(
            SaveCommunitySummaryQuery(
                community_id=community_id, summary=summary, key_entities=key_entities
            )
        )

    async def personalized_pagerank(
        self,
        seed_instance_ids: List[str],
        top_k: int = 20,
        damping_factor: float = 0.85,
        projection_name: str = "instance_graph",
    ) -> List[Dict[str, Any]]:
        return await self._fetch_all(
            PersonalizedPageRankQuery(
                seed_ids=seed_instance_ids,
                projection=projection_name,
                damping=damping_factor,
                top_k=top_k,
            )
        )
