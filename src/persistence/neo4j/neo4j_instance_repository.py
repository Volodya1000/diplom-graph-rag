import logging
from typing import List
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.graph_components.nodes import InstanceNode
from src.application.dtos.extraction_dtos import ResolvedTriple
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from src.persistence.neo4j.mappers.node_mappers import (
    map_to_instance,
    map_to_triple_dict,
)
from .queries.instance_queries import (
    SaveInstanceQuery,
    SaveInstanceRelationQuery,
    FindCandidatesByVectorQuery,
    GetInstancesByChunkQuery,
    GetTriplesByChunkQuery,
    GetInstancesByDocumentQuery,
    GetAllInstancesQuery,
    TransferAliasIncomingEdgesQuery,
    TransferAliasOutgoingEdgesQuery,
    TransferAliasMentionedInQuery,
    UpdateCanonicalInstanceQuery,
    DeleteAliasInstancesQuery,
)

logger = logging.getLogger(__name__)


class Neo4jInstanceRepository(Neo4jBaseRepository, IInstanceRepository):
    def __init__(self, session_manager):
        super().__init__(session_manager)

    async def save_instance(self, instance: InstanceNode) -> None:
        query = SaveInstanceQuery(
            instance_id=instance.instance_id,
            props=instance.model_dump(exclude={"instance_id", "embedding"}),
            embedding=instance.embedding,
        )
        await self._execute(query)

    async def save_instance_relation(self, triple: ResolvedTriple) -> None:
        query = SaveInstanceRelationQuery(
            source_id=triple.source_instance_id,
            target_id=triple.target_instance_id,
            relation_name=triple.relation_name,
            chunk_id=triple.chunk_id,
        )
        await self._execute(query)

    async def find_candidates_by_vector(
        self, embedding: List[float], limit: int = 10
    ) -> List[InstanceNode]:
        threshold = self._settings.vector_search_threshold
        try:
            query = FindCandidatesByVectorQuery(
                embedding=embedding, limit=limit, threshold=threshold
            )
            data = await self._fetch_all(query)
            return [map_to_instance(r) for r in data]
        except Exception as e:
            logger.warning(f"⚠️ Vector search недоступен: {e.__class__.__name__}: {e}")
            return []

    async def get_instances_by_chunk(self, chunk_id: str) -> List[InstanceNode]:
        query = GetInstancesByChunkQuery(chunk_id=chunk_id)
        data = await self._fetch_all(query)
        return [map_to_instance(r) for r in data]

    async def get_triples_by_chunk(self, chunk_id: str) -> List[dict]:
        query = GetTriplesByChunkQuery(chunk_id=chunk_id)
        data = await self._fetch_all(query)
        return [map_to_triple_dict(r) for r in data]

    async def get_instances_by_document(self, doc_id: str) -> List[InstanceNode]:
        query = GetInstancesByDocumentQuery(doc_id=doc_id)
        data = await self._fetch_all(query)
        return [map_to_instance(r) for r in data]

    async def merge_instances(
        self,
        canonical_id: str,
        canonical_name: str,
        alias_ids: List[str],
        aliases: List[str],
    ) -> None:
        if not alias_ids:
            return
        await self._execute(
            TransferAliasIncomingEdgesQuery(
                alias_ids=alias_ids, canonical_id=canonical_id
            )
        )
        await self._execute(
            TransferAliasOutgoingEdgesQuery(
                alias_ids=alias_ids, canonical_id=canonical_id
            )
        )
        await self._execute(
            TransferAliasMentionedInQuery(
                alias_ids=alias_ids, canonical_id=canonical_id
            )
        )
        await self._execute(
            UpdateCanonicalInstanceQuery(
                canonical_id=canonical_id,
                canonical_name=canonical_name,
                aliases=aliases,
            )
        )
        await self._execute(DeleteAliasInstancesQuery(alias_ids=alias_ids))
        logger.info(
            f"🔗 Merged {len(alias_ids)} aliases → «{canonical_name}» ({canonical_id[:8]}…)"
        )

    async def get_all_instances(self) -> List[InstanceNode]:
        query = GetAllInstancesQuery()
        data = await self._fetch_all(query)
        return [map_to_instance(r) for r in data]
