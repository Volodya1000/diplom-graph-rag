from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime
import uuid

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