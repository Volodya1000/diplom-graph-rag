from abc import ABC, abstractmethod
from typing import List

from src.domain.ontology.shema import SchemaClass, SchemaRelation


class ISchemaRepository(ABC):
    """T-Box: классы онтологии, допустимые отношения, индексы."""

    @abstractmethod
    async def ensure_indexes(self) -> None: ...

    @abstractmethod
    async def get_tbox_classes(self) -> List[SchemaClass]: ...

    @abstractmethod
    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None: ...

    @abstractmethod
    async def get_schema_relations(self) -> List[SchemaRelation]: ...

    @abstractmethod
    async def save_schema_relations(
        self, relations: List[SchemaRelation],
    ) -> None: ...