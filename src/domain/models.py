from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid
from dataclasses import dataclass, field


class SchemaStatus(str, Enum):
    CORE = "core"
    DRAFT = "draft"


# --- Исходники ---
class DocumentNode(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)


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


@dataclass
class DocumentAggregate:
    document: DocumentNode
    chunks: List[ChunkNode]

    def build_edges(self) -> List[GraphEdge]:
        edges: List[GraphEdge] = []

        for chunk in self.chunks:
            edges.append(GraphEdge(
                relation_type=GraphRelationType.HAS_CHUNK,
                source_id=self.document.doc_id,
                target_id=chunk.chunk_id
            ))

        for i in range(len(self.chunks) - 1):
            edges.append(GraphEdge(
                relation_type=GraphRelationType.NEXT_CHUNK,
                source_id=self.chunks[i].chunk_id,
                target_id=self.chunks[i + 1].chunk_id
            ))
            edges.append(GraphEdge(
                relation_type=GraphRelationType.PREV_CHUNK,
                source_id=self.chunks[i + 1].chunk_id,
                target_id=self.chunks[i].chunk_id
            ))
        return edges


@dataclass
class InstanceAggregate:
    instance: InstanceNode

    def build_edges(self) -> List[GraphEdge]:
        return [
            GraphEdge(
                relation_type=GraphRelationType.INSTANCE_OF,
                source_id=self.instance.instance_id,
                target_id=self.instance.class_name
            ),
            GraphEdge(
                relation_type=GraphRelationType.MENTIONED_IN,
                source_id=self.instance.instance_id,
                target_id=self.instance.chunk_id
            )
        ]