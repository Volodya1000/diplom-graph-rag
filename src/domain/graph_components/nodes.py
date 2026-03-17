import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


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


class InstanceNode(BaseModel):
    instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    class_name: str
    chunk_id: str
    embedding: Optional[List[float]] = None
