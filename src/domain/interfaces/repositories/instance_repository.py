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