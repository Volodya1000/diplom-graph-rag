import logging
from typing import List
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
from src.domain.graph_components.edges import GraphEdge
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from .queries.edge_queries import SaveEdgeQuery

logger = logging.getLogger(__name__)


class Neo4jEdgeRepository(Neo4jBaseRepository, IEdgeRepository):
    def __init__(self, session_manager):
        super().__init__(session_manager)

    async def save_edges(self, edges: List[GraphEdge]) -> None:
        if not edges:
            return
        for edge in edges:
            query = SaveEdgeQuery(
                relation_type=edge.relation_type.value,
                source_id=edge.source_id,
                target_id=edge.target_id,
            )
            await self._execute(query)
