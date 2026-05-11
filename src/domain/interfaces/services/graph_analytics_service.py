from abc import ABC, abstractmethod
from typing import Any

from src.domain.models.community import GraphCommunity


class IGraphAnalyticsService(ABC):
    @abstractmethod
    async def ensure_projection(
        self,
        projection_name: str = "instance_graph",
    ) -> None: ...
    @abstractmethod
    async def drop_projection(
        self,
        projection_name: str = "instance_graph",
    ) -> None: ...
    @abstractmethod
    async def detect_communities(
        self,
        algorithm: str = "leiden",
        projection_name: str = "instance_graph",
        write_property: str = "community_id",
    ) -> int: ...
    @abstractmethod
    async def get_communities(self) -> list[GraphCommunity]: ...
    @abstractmethod
    async def get_community_members(
        self,
        community_id: int,
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def save_community_summary(
        self,
        community_id: int,
        summary: str,
        key_entities: list[str],
        name: str = "",
    ) -> None: ...
    @abstractmethod
    async def personalized_pagerank(
        self,
        seed_instance_ids: list[str],
        top_k: int = 20,
        damping_factor: float = 0.85,
        projection_name: str = "instance_graph",
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def cleanup_small_communities(self, min_size: int) -> int: ...
