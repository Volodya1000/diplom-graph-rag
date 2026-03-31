from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .base import Neo4jQuery
from src.domain.models.nodes import DocumentNode, ChunkNode
from src.persistence.neo4j.mappers.node_mappers import map_to_document, map_to_chunk


@dataclass
class SaveDocumentQuery(Neo4jQuery[Any]):
    doc_id: str
    props: Dict[str, Any]

    def get_query(self) -> str:
        return """
            MERGE (d:Document {doc_id: $doc_id})
            SET d += $props
        """

    def get_params(self) -> Dict[str, Any]:
        return {"doc_id": self.doc_id, "props": self.props}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class SaveChunkQuery(Neo4jQuery[Any]):
    chunk_id: str
    props: Dict[str, Any]
    embedding: Optional[List[float]] = None

    def get_query(self) -> str:
        if self.embedding:
            return """
                MERGE (c:Chunk {chunk_id: $chunk_id})
                SET c += $props
                WITH c
                CALL db.create.setNodeVectorProperty(c, 'embedding', $embedding)
            """
        return """
            MERGE (c:Chunk {chunk_id: $chunk_id})
            SET c += $props
        """

    def get_params(self) -> Dict[str, Any]:
        p: Dict[str, Any] = {"chunk_id": self.chunk_id, "props": self.props}
        if self.embedding:
            p["embedding"] = self.embedding
        return p

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class GetDocumentByFilenameQuery(Neo4jQuery[DocumentNode]):
    filename: str

    def get_query(self) -> str:
        return """
            MATCH (d:Document {filename: $filename})
            RETURN d.doc_id AS doc_id,
                   d.filename AS filename,
                   d.upload_date AS upload_date
        """

    def get_params(self) -> Dict[str, Any]:
        return {"filename": self.filename}

    def map_record(self, record: Dict[str, Any]) -> DocumentNode:
        return map_to_document(record)


@dataclass
class GetChunksByDocumentQuery(Neo4jQuery[ChunkNode]):
    doc_id: str

    def get_query(self) -> str:
        return """
            MATCH (c:Chunk {doc_id: $doc_id})
            RETURN c.chunk_id AS chunk_id,
                   c.doc_id AS doc_id,
                   c.chunk_index AS chunk_index,
                   c.text AS text,
                   c.headings AS headings,
                   c.start_page AS start_page,
                   c.end_page AS end_page,
                   c.embedding AS embedding
            ORDER BY c.chunk_index
        """

    def get_params(self) -> Dict[str, Any]:
        return {"doc_id": self.doc_id}

    def map_record(self, record: Dict[str, Any]) -> ChunkNode:
        return map_to_chunk(record)
