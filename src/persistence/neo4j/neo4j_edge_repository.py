"""Структурные рёбра графа (HAS_CHUNK, NEXT_CHUNK, INSTANCE_OF, …)."""

import logging
from typing import List

from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
from src.domain.graph_components.edges import GraphEdge
from src.persistence.neo4j.base_repository import Neo4jBaseRepository

logger = logging.getLogger(__name__)


class Neo4jEdgeRepository(Neo4jBaseRepository, IEdgeRepository):

    async def save_edges(self, edges: List[GraphEdge]) -> None:
        if not edges:
            return
        async with self._sm.session() as s:
            for edge in edges:
                rel_type = edge.relation_type.value
                # rel_type — значение из enum GraphRelationType,
                # набор фиксирован → инъекция невозможна
                query = f"""
                    MATCH (source)
                    WHERE (source:Document  AND source.doc_id      = $source_id)
                       OR (source:Chunk     AND source.chunk_id    = $source_id)
                       OR (source:Instance  AND source.instance_id = $source_id)
                    MATCH (target)
                    WHERE (target:Chunk       AND target.chunk_id = $target_id)
                       OR (target:SchemaClass AND target.name     = $target_id)
                    MERGE (source)-[:{rel_type}]->(target)
                """
                await s.run(query, {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                })