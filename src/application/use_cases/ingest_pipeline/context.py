from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from src.domain.models.nodes import ChunkNode, DocumentNode


@dataclass
class IngestContext:
    """Хранит состояние в процессе прохождения пайплайна индексации."""

    file_path: Path
    skip_synonyms: bool

    # Заполняются в процессе:
    document: DocumentNode | None = None
    domain_chunks: list[ChunkNode] = field(default_factory=list)

    # Статистика и кеш:
    saved_instance_ids: set[str] = field(default_factory=set)
    total_entities: int = 0
    total_triples: int = 0

    @property
    def total_chunks(self) -> int:
        return len(self.domain_chunks)


class IIngestStep(ABC):
    """Единый интерфейс для всех шагов индексации."""

    @abstractmethod
    async def execute(self, ctx: IngestContext) -> None:
        """Выполняет один шаг пайплайна, модифицируя IngestContext."""
