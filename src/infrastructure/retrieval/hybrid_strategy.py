import logging
from typing import List
from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy
from src.domain.models.search import RetrievalResult

logger = logging.getLogger(__name__)


class HybridStrategy(IRetrievalStrategy):
    def __init__(self, strategies: List[IRetrievalStrategy]):
        self._strategies = strategies

    @property
    def name(self) -> str:
        return f"hybrid({'+'.join(s.name for s in self._strategies)})"

    async def retrieve(
        self, query: str, query_embedding: List[float], top_k: int = 10
    ) -> RetrievalResult:
        merged = RetrievalResult(metadata={"strategy": self.name, "sub_strategies": []})
        seen_chunks, seen_triples = set(), set()

        for strategy in self._strategies:
            result = await strategy.retrieve(query, query_embedding, top_k)
            for chunk in result.chunks:
                if chunk.chunk_id not in seen_chunks:
                    merged.chunks.append(chunk)
                    seen_chunks.add(chunk.chunk_id)
            for triple in result.triples:
                key = (triple.subject, triple.predicate, triple.object)
                if key not in seen_triples:
                    merged.triples.append(triple)
                    seen_triples.add(key)
            merged.communities.extend(result.communities)
            merged.metadata["sub_strategies"].append(
                {"name": strategy.name, "chunks": len(result.chunks)}
            )

        merged.chunks.sort(key=lambda c: c.score, reverse=True)
        return merged
