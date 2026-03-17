from abc import ABC, abstractmethod
from typing import List

from src.domain.graph_components.nodes import InstanceNode
from src.application.dtos.extraction_dtos import ResolvedTriple


class IInstanceRepository(ABC):
    """Экземпляры сущностей, vector search, семантические связи."""

    @abstractmethod
    async def save_instance(self, instance: InstanceNode) -> None: ...

    @abstractmethod
    async def save_instance_relation(
        self, triple: ResolvedTriple,
    ) -> None: ...

    @abstractmethod
    async def find_candidates_by_vector(
        self, embedding: List[float], limit: int = 10,
    ) -> List[InstanceNode]: ...

    @abstractmethod
    async def get_instances_by_chunk(
        self, chunk_id: str,
    ) -> List[InstanceNode]: ...

    @abstractmethod
    async def get_triples_by_chunk(
        self, chunk_id: str,
    ) -> List[dict]: ...

    @abstractmethod
    async def get_instances_by_document(
            self, doc_id: str,
    ) -> List[InstanceNode]:
        """Все сущности документа (через чанки)."""
        ...

    @abstractmethod
    async def merge_instances(
            self,
            canonical_id: str,
            canonical_name: str,
            alias_ids: List[str],
            aliases: List[str],
    ) -> None:
        """
        Мержит alias-ноды в каноническую:
        - Переносит все рёбра на canonical_id
        - Обновляет aliases[]
        - Удаляет alias-ноды
        """
        ...

    @abstractmethod
    async def get_all_instances(self) -> List[InstanceNode]:
        """Все Instance-ноды в графе (для community detection)."""
        ...