import logging
from typing import List
from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy
from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.models.search import RetrievalResult, RetrievedChunk, RetrievedTriple
from src.persistence.neo4j.session_manager import Neo4jSessionManager

logger = logging.getLogger(__name__)


class PPRStrategy(IRetrievalStrategy):
    def __init__(
        self,
        session_manager: Neo4jSessionManager,
        instance_repo: IInstanceRepository,
        analytics: IGraphAnalyticsService,
        ppr_top_k: int = 20,
        damping: float = 0.85,
    ):
        self._sm = session_manager
        self._instance_repo = instance_repo
        self._analytics = analytics
        self._ppr_top_k = ppr_top_k
        self._damping = damping

    @property
    def name(self) -> str:
        return "personalized_pagerank"

    async def retrieve(
        self, query: str, query_embedding: List[float], top_k: int = 10
    ) -> RetrievalResult:
        seeds = await self._instance_repo.find_candidates_by_vector(
            query_embedding, limit=top_k
        )
        if not seeds:
            return RetrievalResult(metadata={"strategy": self.name, "seeds": 0})

        seed_ids = [c.instance_id for c in seeds]
        await self._analytics.ensure_projection()
        ppr_results = await self._analytics.personalized_pagerank(
            seed_ids, self._ppr_top_k, self._damping
        )

        chunk_ids = {r["chunk_id"] for r in ppr_results if r.get("chunk_id")}
        chunks = await self._load_chunks(list(chunk_ids))
        triples = await self._load_triples_between(
            {r["instance_id"] for r in ppr_results}
        )

        return RetrievalResult(
            chunks=chunks,
            triples=triples,
            metadata={
                "strategy": self.name,
                "seeds": len(seed_ids),
                "ppr_nodes": len(ppr_results),
            },
        )

    async def _load_chunks(self, chunk_ids: List[str]) -> List[RetrievedChunk]:
        if not chunk_ids:
            return []
        query = """
        UNWIND $ids AS cid MATCH (c:Chunk {chunk_id: cid}) MATCH (d:Document {doc_id: c.doc_id})
        RETURN c.chunk_id AS chunk_id, c.text AS text, c.chunk_index AS chunk_index, c.start_page AS start_page, c.end_page AS end_page, d.filename AS filename
        """
        async with self._sm.session() as s:
            data = await (await s.run(query, {"ids": chunk_ids})).data()
        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                text=r["text"],
                score=0.8,
                chunk_index=r.get("chunk_index", 0),
                start_page=r.get("start_page", 0),
                end_page=r.get("end_page", 0),
                source_filename=r.get("filename"),
            )
            for r in data
        ]

    async def _load_triples_between(self, instance_ids: set) -> List[RetrievedTriple]:
        if len(instance_ids) < 2:
            return []
        query = """
        MATCH (src:Instance)-[r]->(tgt:Instance) WHERE src.instance_id IN $ids AND tgt.instance_id IN $ids AND type(r) <> 'MENTIONED_IN' AND type(r) <> 'INSTANCE_OF'
        RETURN src.name AS s_name, src.class_name AS s_type, type(r) AS predicate, tgt.name AS o_name, tgt.class_name AS o_type
        """
        async with self._sm.session() as s:
            data = await (await s.run(query, {"ids": list(instance_ids)})).data()
        return [
            RetrievedTriple(
                subject=r["s_name"],
                subject_type=r["s_type"],
                predicate=r["predicate"],
                object=r["o_name"],
                object_type=r["o_type"],
            )
            for r in data
        ]
