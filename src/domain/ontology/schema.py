from enum import StrEnum

from pydantic import BaseModel


class SchemaStatus(StrEnum):
    CORE = "core"
    DRAFT = "draft"


class SchemaClass(BaseModel):
    name: str
    status: SchemaStatus = SchemaStatus.DRAFT
    description: str = ""
    parent: str | None = None


class SchemaRelation(BaseModel):
    source_class: str
    relation_name: str
    target_class: str
    status: SchemaStatus = SchemaStatus.DRAFT
    description: str = ""
