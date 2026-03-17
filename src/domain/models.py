"""
Доменные модели: узлы, онтология, DTO, рёбра.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ===================================================================
# СТАТУСЫ
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
    name: str
    status: SchemaStatus = SchemaStatus.DRAFT
    description: str = ""
    parent: Optional[str] = None


class SchemaRelation(BaseModel):
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
    subject: str
    predicate: str
    object: str


class ExtractionResult(BaseModel):
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
    source_instance_id: str
    relation_name: str
    target_instance_id: str
    chunk_id: str


# ===================================================================
# СТРУКТУРНЫЕ РЁБРА
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
    result = re.sub(r"[\s\-]+", "_", predicate.strip())
    result = _RE_NON_ALNUM.sub("", result)
    return result.upper() or "RELATED_TO"