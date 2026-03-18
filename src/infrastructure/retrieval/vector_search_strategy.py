"""
LOCAL стратегия: vector search по чанкам + окружающие тройки.

Самая простая и быстрая — классический RAG.
"""

import logging
from typing import List

from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.value_objects.search_context import (
    RetrievalResult,
    RetrievedChunk,
    RetrievedTriple,
)
from src.persistence.neo4j.session_manager import Neo4jSessionManager

logger = logging.getLogger(__name__)


class VectorSearchStrategy(IRetrievalStrategy):
    """Локальный поиск: vector similarity по чанкам → тройки из чанков."""

    def __init__(
        self,
        session_manager: Neo4jSessionManager,
        instance_repo: IInstanceRepository,
    ):
        self._sm = session_manager
        self._instance_repo = instance_repo

    @property
    def name(self) -> str:
        return "vector_search_local"

    async def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> RetrievalResult:

        # 1. Vector search по чанкам
        chunks = await self._search_chunks(query_embedding, top_k)

        # 2. Тройки из найденных чанков
        triples: list[RetrievedTriple] = []
        for chunk in chunks:
            raw_triples = await self._instance_repo.get_triples_by_chunk(
                chunk.chunk_id,
            )
            for t in raw_triples:
                triples.append(
                    RetrievedTriple(
                        subject=t["subject_name"],
                        subject_type=t["subject_type"],
                        predicate=t["predicate"],
                        object=t["object_name"],
                        object_type=t["object_type"],
                        score=chunk.score,
                    )
                )

        return RetrievalResult(
            chunks=chunks,
            triples=triples,
            metadata={"strategy": self.name},
        )

    async def _search_chunks(
        self,
        embedding: List[float],
        limit: int,
    ) -> List[RetrievedChunk]:
        query = """
        CALL db.index.vector.queryNodes(
            'chunk_embedding', $limit, $embedding
        )
        YIELD node AS c, score
        WHERE score >= 0.5
        RETURN c.chunk_id    AS chunk_id,
               c.text        AS text,
               c.chunk_index AS chunk_index,
               c.doc_id      AS doc_id,
               score
        ORDER BY score DESC
        """
        async with self._sm.session() as s:
            res = await s.run(query, {
                "embedding": embedding,
                "limit": limit,
            })
            data = await res.data()

        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                text=r["text"],
                score=r["score"],
                chunk_index=r.get("chunk_index", 0),
            )
            for r in data
        ]