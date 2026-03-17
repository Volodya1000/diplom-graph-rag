"""Value Objects для поисковой подсистемы."""

from __future__ import annotations

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    """Режим поиска — определяет стратегию."""
    LOCAL = "local"           # vector + ближайшее окружение
    GLOBAL = "global"         # community summaries
    LOCAL_PPR = "local_ppr"   # vector seed → Personalized PageRank
    HYBRID = "hybrid"         # комбинация local + global


class RetrievedChunk(BaseModel):
    """Один найденный чанк с метаданными релевантности."""
    chunk_id: str
    text: str
    score: float = 0.0
    source_filename: Optional[str] = None
    chunk_index: int = 0


class RetrievedTriple(BaseModel):
    """Тройка, найденная в контексте."""
    subject: str
    subject_type: str
    predicate: str
    object: str
    object_type: str
    score: float = 0.0


class RetrievedCommunity(BaseModel):
    """Сводка по сообществу графа."""
    community_id: int
    summary: str
    key_entities: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0


class RetrievalResult(BaseModel):
    """
    Результат работы одной стратегии.
    Стратегия заполняет то, что нашла — поля необязательны.
    """
    chunks: List[RetrievedChunk] = Field(default_factory=list)
    triples: List[RetrievedTriple] = Field(default_factory=list)
    communities: List[RetrievedCommunity] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)