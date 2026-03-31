from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SchemaStatus(str, Enum):
    CORE = "core"
    DRAFT = "draft"


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
