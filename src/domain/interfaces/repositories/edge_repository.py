from abc import ABC, abstractmethod

from src.domain.models.edges import GraphEdge


class IEdgeRepository(ABC):
    @abstractmethod
    async def save_edges(self, edges: list[GraphEdge]) -> None: ...
