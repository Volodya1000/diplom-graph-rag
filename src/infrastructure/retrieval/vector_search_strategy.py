import logging
from typing import List
from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.models.search import RetrievalResult, RetrievedChunk, RetrievedTriple
from src.persistence.neo4j.session_manager import Neo4jSessionManager

logger = logging.getLogger(__name__)


class VectorSearchStrategy(IRetrievalStrategy):
    def __init__(
        self, session_manager: Neo4jSessionManager, instance_repo: IInstanceRepository
    ):
        self._sm = session_manager
        self._instance_repo = instance_repo

    @property
    def name(self) -> str:
        return "vector_search_local"

    async def retrieve(
        self, query: str, query_embedding: List[float], top_k: int = 10
    ) -> RetrievalResult:
        chunks = await self._search_chunks(query_embedding, top_k)
        triples = []
        for chunk in chunks:
            for t in await self._instance_repo.get_triples_by_chunk(chunk.chunk_id):
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
            chunks=chunks, triples=triples, metadata={"strategy": self.name}
        )

    async def _search_chunks(
        self, embedding: List[float], limit: int
    ) -> List[RetrievedChunk]:
        query = """
        CALL db.index.vector.queryNodes('chunk_embedding', $limit, $embedding)
        YIELD node AS c, score
        WHERE score >= 0.5
        MATCH (d:Document {doc_id: c.doc_id})
        RETURN c.chunk_id AS chunk_id, c.text AS text, c.chunk_index AS chunk_index, c.start_page AS start_page, c.end_page AS end_page, d.filename AS filename, score
        ORDER BY score DESC
        """
        async with self._sm.session() as s:
            data = await (
                await s.run(query, {"embedding": embedding, "limit": limit})
            ).data()
        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                text=r["text"],
                score=r["score"],
                chunk_index=r.get("chunk_index", 0),
                start_page=r.get("start_page", 0),
                end_page=r.get("end_page", 0),
                source_filename=r.get("filename"),
            )
            for r in data
        ]
