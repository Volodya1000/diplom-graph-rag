from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Optional

from src.domain.graph_components.nodes import DocumentNode, ChunkNode


@dataclass
class IngestContext:
    """Хранит состояние в процессе прохождения пайплайна индексации."""

    file_path: Path
    skip_synonyms: bool

    # Заполняются в процессе:
    document: Optional[DocumentNode] = None
    domain_chunks: List[ChunkNode] = field(default_factory=list)

    # Статистика и кеш:
    saved_instance_ids: Set[str] = field(default_factory=set)
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
        pass
