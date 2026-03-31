import logging
from typing import List
from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy
from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.models.search import RetrievalResult, RetrievedCommunity
from src.persistence.neo4j.session_manager import Neo4jSessionManager

logger = logging.getLogger(__name__)


class CommunityStrategy(IRetrievalStrategy):
    def __init__(
        self,
        analytics: IGraphAnalyticsService,
        embedder: IEmbeddingService,
        session_manager: Neo4jSessionManager,
    ):
        self._analytics = analytics
        self._embedder = embedder
        self._sm = session_manager

    @property
    def name(self) -> str:
        return "community_global"

    async def retrieve(
        self, query: str, query_embedding: List[float], top_k: int = 5
    ) -> RetrievalResult:
        communities = await self._analytics.get_communities()
        if not communities:
            return RetrievalResult(metadata={"strategy": self.name})

        scored = []
        for comm in communities:
            if not comm.summary:
                continue
            summary_emb = await self._embedder.embed_text(comm.summary)
            sim = sum(x * y for x, y in zip(query_embedding, summary_emb)) / (
                (sum(x**2 for x in query_embedding) ** 0.5)
                * (sum(x**2 for x in summary_emb) ** 0.5)
                or 1
            )
            scored.append(
                RetrievedCommunity(
                    community_id=comm.community_id,
                    summary=comm.summary,
                    key_entities=comm.key_entities,
                    relevance_score=sim,
                )
            )

        scored.sort(key=lambda c: c.relevance_score, reverse=True)
        return RetrievalResult(
            communities=scored[:top_k],
            metadata={"strategy": self.name, "total_communities": len(scored)},
        )
