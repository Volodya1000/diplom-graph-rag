from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass, field


class SchemaStatus(str, Enum):
    CORE = "core"
    DRAFT = "draft"


# --- Исходники ---
class DocumentNode(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChunkNode(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str
    chunk_index: int
    text: str
    headings: List[str] = Field(default_factory=list)
    start_page: int = 0
    end_page: int = 0
    embedding: Optional[List[float]] = None


# --- Онтология (T-Box) ---
class SchemaClass(BaseModel):
    name: str
    status: SchemaStatus = SchemaStatus.DRAFT
    description: str = ""                              # ← ДОБАВЛЕНО


class SchemaRelation(BaseModel):
    source_class: str
    relation_name: str
    target_class: str
    status: SchemaStatus = SchemaStatus.DRAFT


# --- DTO от LLM ---
class RawExtractedEntity(BaseModel):
    name: str
    type: str


# --- Экземпляры (A-Box) ---
class InstanceNode(BaseModel):
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    class_name: str
    chunk_id: str
    embedding: Optional[List[float]] = None


# ===================================================================
# ВСЯ ЛОГИКА ГРАФА — ТОЛЬКО ЗДЕСЬ (ДОМЕН)
# ===================================================================
class GraphRelationType(str, Enum):
    HAS_CHUNK     = "HAS_CHUNK"
    NEXT_CHUNK    = "NEXT_CHUNK"
    PREV_CHUNK    = "PREV_CHUNK"
    INSTANCE_OF   = "INSTANCE_OF"
    MENTIONED_IN  = "MENTIONED_IN"


@dataclass(frozen=True)
class GraphEdge:
    relation_type: GraphRelationType
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


