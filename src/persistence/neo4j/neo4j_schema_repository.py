import logging
from typing import List, Dict
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.ontology.schema import SchemaClass, SchemaRelation
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from .queries.schema_queries import (
    CreateInstanceEmbeddingIndexQuery,
    CreateChunkEmbeddingIndexQuery,
    CreateInstanceNameIndexQuery,
    CreateSchemaClassNameIndexQuery,
    GetTboxClassesQuery,
    SaveTboxClassesQuery,
    CreateSubclassOfEdgesQuery,
    GetSchemaRelationsQuery,
    SaveSchemaRelationsQuery,
    GetClassUsageCountsQuery,
)

logger = logging.getLogger(__name__)


class Neo4jSchemaRepository(Neo4jBaseRepository, ISchemaRepository):
    def __init__(self, session_manager):
        super().__init__(session_manager)

    async def ensure_indexes(self) -> None:
        dim = self._settings.embedding_dim
        await self._execute(CreateInstanceEmbeddingIndexQuery(dim=dim))
        await self._execute(CreateChunkEmbeddingIndexQuery(dim=dim))
        await self._execute(CreateInstanceNameIndexQuery())
        await self._execute(CreateSchemaClassNameIndexQuery())
        logger.info(f"📐 Индексы обеспечены (embedding_dim={dim})")

    async def get_tbox_classes(self) -> List[SchemaClass]:
        return await self._fetch_all(GetTboxClassesQuery())

    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None:
        if not classes:
            return
        batch = [
            {
                "name": c.name,
                "status": c.status.value,
                "description": c.description,
                "parent": c.parent,
            }
            for c in classes
        ]
        await self._execute(SaveTboxClassesQuery(batch=batch))
        await self._execute(CreateSubclassOfEdgesQuery(batch=batch))

    async def get_schema_relations(self) -> List[SchemaRelation]:
        return await self._fetch_all(GetSchemaRelationsQuery())

    async def save_schema_relations(self, relations: List[SchemaRelation]) -> None:
        if not relations:
            return
        batch = [
            {
                "source_class": r.source_class,
                "relation_name": r.relation_name,
                "target_class": r.target_class,
                "status": r.status.value,
                "description": r.description,
            }
            for r in relations
        ]
        await self._execute(SaveSchemaRelationsQuery(batch=batch))

    async def get_class_usage_counts(self) -> Dict[str, int]:
        data = await self._fetch_all(GetClassUsageCountsQuery())
        return {r["name"]: r["usage"] for r in data}
