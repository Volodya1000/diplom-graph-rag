from abc import ABC, abstractmethod
from typing import List
from src.domain.models.edges import GraphEdge


class IEdgeRepository(ABC):
    @abstractmethod
    async def save_edges(self, edges: List[GraphEdge]) -> None: ...
