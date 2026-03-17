from abc import ABC, abstractmethod
from typing import List

from domain.graph_components.edges import GraphEdge
from application.dtos.extraction_dtos import ResolvedTriple
from domain.ontology.shema import SchemaClass, SchemaRelation
from domain.graph_components.nodes import DocumentNode, ChunkNode, InstanceNode


class IGraphRepository(ABC):
    # === Инициализация ===
    @abstractmethod
    async def ensure_indexes(self) -> None:
        """Создаёт векторные и прочие индексы (идемпотентно)."""
        ...

    # === Узлы ===
    @abstractmethod
    async def save_document(self, document: DocumentNode) -> None: ...

    @abstractmethod
    async def save_chunk(self, chunk: ChunkNode) -> None: ...

    @abstractmethod
    async def save_instance(self, instance: InstanceNode) -> None: ...

    # === Структурные рёбра ===
    @abstractmethod
    async def save_edges(self, edges: List[GraphEdge]) -> None: ...

    # === T-Box: классы ===
    @abstractmethod
    async def get_tbox_classes(self) -> List[SchemaClass]: ...

    @abstractmethod
    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None: ...

    # === T-Box: отношения ===
    @abstractmethod
    async def get_schema_relations(self) -> List[SchemaRelation]: ...

    @abstractmethod
    async def save_schema_relations(
        self, relations: List[SchemaRelation],
    ) -> None: ...

    # === Семантические связи ===
    @abstractmethod
    async def save_instance_relation(
        self, triple: ResolvedTriple,
    ) -> None: ...

    # === Поиск ===
    @abstractmethod
    async def find_candidates_by_vector(
        self, embedding: List[float], limit: int = 10,
    ) -> List[InstanceNode]: ...

    @abstractmethod
    async def get_document_by_filename(self, filename: str) -> List[DocumentNode]:
        """Возвращает все документы с указанным именем файла."""
        ...

    @abstractmethod
    async def get_chunks_by_document(self, doc_id: str) -> List[ChunkNode]:
        """Возвращает все чанки документа, отсортированные по индексу."""
        ...

    @abstractmethod
    async def get_instances_by_chunk(self, chunk_id: str) -> List[InstanceNode]:
        """Возвращает все сущности, упомянутые в данном чанке."""
        ...

    @abstractmethod
    async def get_triples_by_chunk(self, chunk_id: str) -> List[dict]:
        """
        Возвращает все триплеты, извлечённые из чанка.
        Каждый элемент словаря содержит:
            subject_name, subject_type,
            predicate,
            object_name, object_type
        """