from abc import ABC, abstractmethod
from typing import Any

from src.domain.models.extraction import ResolvedTriple
from src.domain.models.nodes import InstanceNode


class IInstanceRepository(ABC):
    @abstractmethod
    async def save_instance(self, instance: InstanceNode) -> None: ...
    @abstractmethod
    async def save_instance_relation(self, triple: ResolvedTriple) -> None: ...
    @abstractmethod
    async def find_candidates_by_vector(
        self,
        embedding: list[float],
        limit: int = 10,
    ) -> list[InstanceNode]: ...
    @abstractmethod
    async def get_instances_by_chunk(self, chunk_id: str) -> list[InstanceNode]: ...
    @abstractmethod
    async def get_triples_by_chunk(self, chunk_id: str) -> list[dict[str, Any]]: ...
    @abstractmethod
    async def get_instances_by_document(self, doc_id: str) -> list[InstanceNode]: ...
    @abstractmethod
    async def merge_instances(
        self,
        canonical_id: str,
        canonical_name: str,
        alias_ids: list[str],
        aliases: list[str],
    ) -> None: ...
    @abstractmethod
    async def get_all_instances(self) -> list[InstanceNode]: ...
