import logging
from typing import Any

from collections import Counter

from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.models.community import (
    GraphCommunity,
    CommunityDetails,
    CommunityHub,
    CommunityBoundaryNode,
    CommunityNode,
    CommunityEdge,
)
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from src.persistence.neo4j.queries.analytics_queries import (
    CleanupSmallCommunitiesQuery,
    DetectCommunitiesQuery,
    DropProjectionQuery,
    GetCommunitiesQuery,
    GetCommunityMembersQuery,
    GraphExistsQuery,
    GraphProjectQuery,
    PersonalizedPageRankQuery,
    SaveCommunitySummaryQuery,
    GetCommunityDetailsQuery,
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
        algo_call = {"leiden": "gds.leiden.write", "louvain": "gds.louvain.write"}[algorithm]
        data = await self._fetch_all(
            DetectCommunitiesQuery(
                projection=projection_name,
                prop=write_property,
                algo_call=algo_call,
            ),
        )
        count = data[0]["communityCount"]
        logger.info(f"🧩 {algorithm}: {count} сообществ")
        return count

    async def get_communities(self) -> list[GraphCommunity]:
        return await self._fetch_all(GetCommunitiesQuery())

    async def get_community_members(self, community_id: int) -> list[dict[str, Any]]:
        return await self._fetch_all(
            GetCommunityMembersQuery(community_id=community_id),
        )

    async def save_community_summary(
        self,
        community_id: int,
        summary: str,
        key_entities: list[str],
        name: str = "",
    ) -> None:
        await self._execute(
            SaveCommunitySummaryQuery(
                community_id=community_id,
                summary=summary,
                key_entities=key_entities,
                name=name,
            ),
        )

    async def personalized_pagerank(
        self,
        seed_instance_ids: list[str],
        top_k: int = 20,
        damping_factor: float = 0.85,
        projection_name: str = "instance_graph",
    ) -> list[dict[str, Any]]:
        return await self._fetch_all(
            PersonalizedPageRankQuery(
                seed_ids=seed_instance_ids,
                projection=projection_name,
                damping=damping_factor,
                top_k=top_k,
            ),
        )

    async def cleanup_small_communities(self, min_size: int) -> int:
        data = await self._fetch_all(CleanupSmallCommunitiesQuery(min_size=min_size))
        count = data[0] if data else 0
        if count > 0:
            logger.info(
                f"🧹 Удалено {count} узлов из слишком мелких сообществ (размер < {min_size})",
            )
        return count

    async def get_community_details(self, community_id: int) -> CommunityDetails | None:
        data = await self._fetch_all(GetCommunityDetailsQuery(community_id=community_id))
        if not data or data[0]["node_count"] == 0:
            return None

        r = data[0]
        nodes_c = r.get("node_count", 0)
        edges_c = r.get("edge_count", 0)

        density = 0.0
        if nodes_c > 1:
            density = edges_c / (nodes_c * (nodes_c - 1))

        node_types_count = dict(Counter(r.get("raw_node_types", [])).most_common())
        rel_types_count = dict(Counter(r.get("raw_rel_types", [])).most_common())

        # Маппим словари Neo4j в строгие Pydantic модели
        hubs = [CommunityHub(name=h["name"], degree=h["degree"]) for h in r.get("hubs", [])]
        boundary = [CommunityBoundaryNode(name=b["name"], degree=b["degree"]) for b in r.get("boundary_nodes", [])]
        nodes = [CommunityNode(name=n["name"], type=n["type"]) for n in r.get("node_list", [])]
        edges = [CommunityEdge(source=e["source"], type=e["type"], target=e["target"]) for e in r.get("edges", [])]

        return CommunityDetails(
            community_id=r["community_id"],
            name=r.get("name"),
            summary=r.get("summary"),
            node_count=nodes_c,
            edge_count=edges_c,
            density=density,
            hubs=hubs,
            boundary_nodes=boundary,
            dominant_types=node_types_count,
            dominant_relations=rel_types_count,
            document_count=r.get("doc_count", 0),
            documents=r.get("documents", []),
            nodes=nodes,
            edges=edges,
        )
