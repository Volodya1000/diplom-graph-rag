import datetime
from dataclasses import dataclass
from typing import Any

from src.domain.models.nodes import ChunkNode, DocumentNode, DocumentStats
from src.persistence.neo4j.mappers.node_mappers import map_to_chunk, map_to_document

from .base import Neo4jQuery


@dataclass
class SaveDocumentQuery(Neo4jQuery[Any]):
    doc_id: str
    props: dict[str, Any]

    def get_query(self) -> str:
        return """
            MERGE (d:Document {doc_id: $doc_id})
            SET d += $props
        """

    def get_params(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id, "props": self.props}

    def map_record(self, record: dict[str, Any]) -> Any:
        return None


@dataclass
class SaveChunkQuery(Neo4jQuery[Any]):
    chunk_id: str
    props: dict[str, Any]
    embedding: list[float] | None = None

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

    def get_params(self) -> dict[str, Any]:
        p: dict[str, Any] = {"chunk_id": self.chunk_id, "props": self.props}
        if self.embedding:
            p["embedding"] = self.embedding
        return p

    def map_record(self, record: dict[str, Any]) -> Any:
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

    def get_params(self) -> dict[str, Any]:
        return {"filename": self.filename}

    def map_record(self, record: dict[str, Any]) -> DocumentNode:
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

    def get_params(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id}

    def map_record(self, record: dict[str, Any]) -> ChunkNode:
        return map_to_chunk(record)


def map_to_document_stats(record: dict[str, Any]) -> DocumentStats:
    upload_date = record.get("upload_date")

    # Neo4j кастомные даты → Python datetime
    if upload_date is not None and hasattr(upload_date, "to_native"):
        upload_date = upload_date.to_native()

    # runtime защита + помощь type checker'у
    if not isinstance(upload_date, datetime.datetime):
        raise TypeError(f"Invalid upload_date: expected datetime, got {type(upload_date)}")

    return DocumentStats(
        doc_id=record["doc_id"],
        filename=record["filename"],
        upload_date=upload_date,
        chunks_count=record.get("chunks_count", 0),
        entities_count=record.get("entities_count", 0),
        triples_count=record.get("triples_count", 0),
        communities_count=record.get("communities_count", 0),
    )


@dataclass
class GetAllDocumentsStatsQuery(Neo4jQuery[DocumentStats]):
    def get_query(self) -> str:
        return """
            MATCH (d:Document)
            CALL {
                WITH d
                OPTIONAL MATCH (c:Chunk {doc_id: d.doc_id})
                RETURN count(c) AS chunks_count
            }
            CALL {
                WITH d
                OPTIONAL MATCH (i:Instance)-[:MENTIONED_IN]->(c:Chunk {doc_id: d.doc_id})
                RETURN count(DISTINCT i) AS entities_count, count(DISTINCT i.community_id) AS communities_count
            }
            CALL {
                WITH d
                OPTIONAL MATCH (c:Chunk {doc_id: d.doc_id})<-[:MENTIONED_IN]-(src:Instance)-[r]->(tgt:Instance)
                WHERE r.chunk_id = c.chunk_id
                RETURN count(DISTINCT r) AS triples_count
            }
            RETURN d.doc_id AS doc_id, d.filename AS filename, d.upload_date AS upload_date,
                   chunks_count, entities_count, triples_count, communities_count
            ORDER BY d.upload_date DESC
        """

    def get_params(self) -> dict[str, Any]:
        return {}

    def map_record(self, record: dict[str, Any]) -> DocumentStats:
        return map_to_document_stats(record)


@dataclass
class GetDocumentStatsQuery(Neo4jQuery[DocumentStats]):
    doc_id: str

    def get_query(self) -> str:
        return """
            MATCH (d:Document {doc_id: $doc_id})
            CALL {
                WITH d
                OPTIONAL MATCH (c:Chunk {doc_id: d.doc_id})
                RETURN count(c) AS chunks_count
            }
            CALL {
                WITH d
                OPTIONAL MATCH (i:Instance)-[:MENTIONED_IN]->(c:Chunk {doc_id: d.doc_id})
                RETURN count(DISTINCT i) AS entities_count, count(DISTINCT i.community_id) AS communities_count
            }
            CALL {
                WITH d
                OPTIONAL MATCH (c:Chunk {doc_id: d.doc_id})<-[:MENTIONED_IN]-(src:Instance)-[r]->(tgt:Instance)
                WHERE r.chunk_id = c.chunk_id
                RETURN count(DISTINCT r) AS triples_count
            }
            RETURN d.doc_id AS doc_id, d.filename AS filename, d.upload_date AS upload_date,
                   chunks_count, entities_count, triples_count, communities_count
        """

    def get_params(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id}

    def map_record(self, record: dict[str, Any]) -> DocumentStats:
        return map_to_document_stats(record)
