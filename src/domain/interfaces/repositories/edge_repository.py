from abc import ABC, abstractmethod
from typing import List

from src.domain.graph_components.edges import GraphEdge


class IEdgeRepository(ABC):
    """Структурные рёбра графа (HAS_CHUNK, NEXT_CHUNK, INSTANCE_OF, …)."""

    @abstractmethod
    async def save_edges(self, edges: List[GraphEdge]) -> None: ...