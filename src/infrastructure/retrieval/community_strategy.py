"""
GLOBAL стратегия: community summaries → ответ высокого уровня.

Предполагает, что community detection уже выполнен
и summaries сгенерированы.
"""

import logging
from typing import List

from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy
from src.domain.interfaces.services.graph_analytics_service import IGraphAnalyticsService
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.value_objects.search_context import (
    RetrievalResult,
    RetrievedCommunity,
)
from src.persistence.neo4j.session_manager import Neo4jSessionManager

logger = logging.getLogger(__name__)


class CommunityStrategy(IRetrievalStrategy):
    """
    Глобальный поиск по сообществам графа.

    1. Получаем все сообщества с summaries
    2. Ранжируем по релевантности к вопросу (vector sim по summary)
    3. Возвращаем top-k сообществ
    """

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
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> RetrievalResult:

        communities = await self._analytics.get_communities()
        if not communities:
            logger.warning("⚠️ Нет сообществ — запустите community detection")
            return RetrievalResult(metadata={"strategy": self.name})

        # Ранжирование: embed каждый summary, cosine sim с query
        scored: list[RetrievedCommunity] = []
        for comm in communities:
            if not comm.summary:
                continue
            summary_emb = await self._embedder.embed_text(comm.summary)
            sim = self._cosine_sim(query_embedding, summary_emb)
            scored.append(
                RetrievedCommunity(
                    community_id=comm.community_id,
                    summary=comm.summary,
                    key_entities=comm.key_entities,
                    relevance_score=sim,
                )
            )

        scored.sort(key=lambda c: c.relevance_score, reverse=True)
        top = scored[:top_k]

        logger.info(
            f"🌐 Communities: {len(scored)} total, "
            f"returning top {len(top)}"
        )

        return RetrievalResult(
            communities=top,
            metadata={
                "strategy": self.name,
                "total_communities": len(scored),
            },
        )

    @staticmethod
    def _cosine_sim(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)