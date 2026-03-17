"""
Доменные модели: узлы графа, онтология, DTO от LLM, рёбра.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ===================================================================
# СТАТУСЫ ОНТОЛОГИИ
# ===================================================================

class SchemaStatus(str, Enum):
    CORE = "core"
    DRAFT = "draft"


# ===================================================================
# ДОКУМЕНТЫ И ЧАНКИ
# ===================================================================

class DocumentNode(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    upload_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ChunkNode(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    chunk_index: int
    text: str
    headings: List[str] = Field(default_factory=list)
    start_page: int = 0
    end_page: int = 0
    embedding: Optional[List[float]] = None


# ===================================================================
# ОНТОЛОГИЯ (T-BOX)
# ===================================================================

class SchemaClass(BaseModel):
    """Класс онтологии с поддержкой иерархии."""
    name: str
    status: SchemaStatus = SchemaStatus.DRAFT
    description: str = ""
    parent: Optional[str] = None          # ← имя родительского класса


class SchemaRelation(BaseModel):
    """Допустимое отношение между классами онтологии."""
    source_class: str
    relation_name: str
    target_class: str
    status: SchemaStatus = SchemaStatus.DRAFT
    description: str = ""


# ===================================================================
# DTO ОТ LLM
# ===================================================================

class RawExtractedEntity(BaseModel):
    name: str
    type: str


class RawExtractedTriple(BaseModel):
    """Тройка, извлечённая LLM из текста."""
    subject: str       # имя сущности-субъекта
    predicate: str     # имя отношения
    object: str        # имя сущности-объекта


class ExtractionResult(BaseModel):
    """Полный результат извлечения LLM: сущности + тройки."""
    entities: List[RawExtractedEntity] = Field(default_factory=list)
    triples: List[RawExtractedTriple] = Field(default_factory=list)


# ===================================================================
# ЭКЗЕМПЛЯРЫ (A-BOX)
# ===================================================================

class InstanceNode(BaseModel):
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    class_name: str
    chunk_id: str
    embedding: Optional[List[float]] = None


class ResolvedTriple(BaseModel):
    """Тройка с разрешёнными instance_id (готовая к сохранению)."""
    source_instance_id: str
    relation_name: str
    target_instance_id: str
    chunk_id: str


# ===================================================================
# СТРУКТУРНЫЕ РЁБРА ГРАФА
# ===================================================================

class GraphRelationType(str, Enum):
    HAS_CHUNK    = "HAS_CHUNK"
    NEXT_CHUNK   = "NEXT_CHUNK"
    PREV_CHUNK   = "PREV_CHUNK"
    INSTANCE_OF  = "INSTANCE_OF"
    MENTIONED_IN = "MENTIONED_IN"


@dataclass(frozen=True)
class GraphEdge:
    relation_type: GraphRelationType
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


# ===================================================================
# УТИЛИТЫ
# ===================================================================

_RE_NON_ALNUM = re.compile(r"[^A-Za-z0-9_]")


def normalize_predicate(predicate: str) -> str:
    """Нормализует имя предиката → UPPER_SNAKE_CASE."""
    result = re.sub(r"[\s\-]+", "_", predicate.strip())
    result = _RE_NON_ALNUM.sub("", result)
    return result.upper() or "RELATED_TO"