from abc import ABC, abstractmethod

from src.domain.ontology.schema import SchemaClass, SchemaRelation


class ISchemaRepository(ABC):
    """T-Box: классы онтологии, допустимые отношения, индексы."""

    @abstractmethod
    async def ensure_indexes(self) -> None: ...

    @abstractmethod
    async def get_tbox_classes(self) -> list[SchemaClass]: ...

    @abstractmethod
    async def save_tbox_classes(self, classes: list[SchemaClass]) -> None: ...

    @abstractmethod
    async def get_schema_relations(self) -> list[SchemaRelation]: ...

    @abstractmethod
    async def save_schema_relations(
        self,
        relations: list[SchemaRelation],
    ) -> None: ...

    @abstractmethod
    async def get_class_usage_counts(self) -> dict[str, int]:
        """Сколько экземпляров использует каждый класс (для запрета удаления)."""
        ...
