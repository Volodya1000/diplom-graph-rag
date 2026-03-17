"""
HYBRID стратегия: композит из нескольких стратегий.

Composite Pattern: объединяет результаты local + global,
дедуплицирует чанки, мержит тройки.
"""

import logging
from typing import List

from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy
from src.domain.value_objects.search_context import RetrievalResult

logger = logging.getLogger(__name__)


class HybridStrategy(IRetrievalStrategy):
    """
    Объединяет результаты нескольких стратегий.
    Порядок стратегий определяет приоритет при дедупликации.
    """

    def __init__(self, strategies: List[IRetrievalStrategy]):
        if not strategies:
            raise ValueError("HybridStrategy нужна хотя бы одна стратегия")
        self._strategies = strategies

    @property
    def name(self) -> str:
        names = "+".join(s.name for s in self._strategies)
        return f"hybrid({names})"

    async def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
    ) -> RetrievalResult:

        merged = RetrievalResult(
            metadata={"strategy": self.name, "sub_strategies": []},
        )

        seen_chunk_ids: set[str] = set()
        seen_triple_keys: set[tuple] = set()

        for strategy in self._strategies:
            logger.info(f"🔀 Hybrid → {strategy.name}")
            result = await strategy.retrieve(
                query, query_embedding, top_k,
            )

            # Дедупликация чанков
            for chunk in result.chunks:
                if chunk.chunk_id not in seen_chunk_ids:
                    merged.chunks.append(chunk)
                    seen_chunk_ids.add(chunk.chunk_id)

            # Дедупликация троек
            for triple in result.triples:
                key = (
                    triple.subject, triple.predicate, triple.object,
                )
                if key not in seen_triple_keys:
                    merged.triples.append(triple)
                    seen_triple_keys.add(key)

            # Communities (не дедуплицируем — разные стратегии дают разные)
            merged.communities.extend(result.communities)

            merged.metadata["sub_strategies"].append({
                "name": strategy.name,
                "chunks": len(result.chunks),
                "triples": len(result.triples),
                "communities": len(result.communities),
            })

        # Сортировка по score
        merged.chunks.sort(key=lambda c: c.score, reverse=True)

        logger.info(
            f"🔀 Hybrid merged: {len(merged.chunks)} chunks, "
            f"{len(merged.triples)} triples, "
            f"{len(merged.communities)} communities"
        )

        return merged