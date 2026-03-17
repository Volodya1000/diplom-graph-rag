"""
Абстракция над графовой аналитикой (Neo4j GDS).

Domain-слой не знает о GDS — только о результатах.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from src.domain.value_objects.graph_community import GraphCommunity


class IGraphAnalyticsService(ABC):
    """Аналитика графа: community detection, PPR, centrality."""

    # ============= GRAPH PROJECTION =============

    @abstractmethod
    async def ensure_projection(
        self,
        projection_name: str = "instance_graph",
    ) -> None:
        """
        Создаёт/обновляет проекцию графа для алгоритмов GDS.
        Идемпотентно.
        """
        ...

    @abstractmethod
    async def drop_projection(
        self,
        projection_name: str = "instance_graph",
    ) -> None:
        """Удаляет проекцию (если существует)."""
        ...

    # ============= COMMUNITY DETECTION =============

    @abstractmethod
    async def detect_communities(
        self,
        algorithm: str = "leiden",
        projection_name: str = "instance_graph",
        write_property: str = "community_id",
    ) -> int:
        """
        Запускает community detection и записывает community_id
        в свойства нод.

        Returns:
            Количество найденных сообществ.
        """
        ...

    @abstractmethod
    async def get_communities(self) -> List[GraphCommunity]:
        """Возвращает все сообщества с их участниками."""
        ...

    @abstractmethod
    async def get_community_members(
        self, community_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Возвращает участников сообщества с их связями.

        Returns:
            [{"instance_id": ..., "name": ..., "class_name": ..., "relations": [...]}]
        """
        ...

    # ============= PERSONALIZED PAGERANK =============

    @abstractmethod
    async def personalized_pagerank(
        self,
        seed_instance_ids: List[str],
        top_k: int = 20,
        damping_factor: float = 0.85,
        projection_name: str = "instance_graph",
    ) -> List[Dict[str, Any]]:
        """
        Personalized PageRank от заданных seed-нод.

        Returns:
            [{"instance_id": ..., "name": ..., "class_name": ...,
              "score": ..., "chunk_id": ...}]
            отсортированные по score DESC.
        """
        ...