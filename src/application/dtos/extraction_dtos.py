from pydantic import BaseModel


class RawExtractedEntity(BaseModel):
    name: str
    type: str


class RawExtractedTriple(BaseModel):
    subject: str
    predicate: str
    object: str


class ResolvedTriple(BaseModel):
    source_instance_id: str
    relation_name: str
    target_instance_id: str
    chunk_id: str
