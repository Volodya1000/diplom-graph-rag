"""
Чистые функции маппинга: Neo4j record → Domain object.
"""

from typing import Dict, Any

from neo4j.time import DateTime as Neo4jDateTime

from src.domain.graph_components.nodes import DocumentNode, ChunkNode, InstanceNode
from src.domain.ontology.schema import SchemaClass, SchemaRelation


def map_to_document(record: Dict[str, Any]) -> DocumentNode:
    upload_date = record["upload_date"]
    if isinstance(upload_date, Neo4jDateTime):
        upload_date = upload_date.to_native()
    return DocumentNode(
        doc_id=record["doc_id"],
        filename=record["filename"],
        upload_date=upload_date,
    )


def map_to_chunk(record: Dict[str, Any]) -> ChunkNode:
    return ChunkNode(
        chunk_id=record["chunk_id"],
        doc_id=record["doc_id"],
        chunk_index=record["chunk_index"],
        text=record["text"],
        headings=record.get("headings") or [],
        start_page=record.get("start_page", 0),
        end_page=record.get("end_page", 0),
        embedding=record.get("embedding"),
    )


def map_to_instance(record: Dict[str, Any]) -> InstanceNode:
    return InstanceNode(
        instance_id=record["instance_id"],
        name=record["name"],
        class_name=record["class_name"],
        chunk_id=record["chunk_id"],
        embedding=record.get("embedding"),
    )


def map_to_schema_class(record: Dict[str, Any]) -> SchemaClass:
    return SchemaClass(
        name=record["name"],
        status=record["status"],
        description=record.get("description") or "",
        parent=record.get("parent"),
    )


def map_to_schema_relation(record: Dict[str, Any]) -> SchemaRelation:
    return SchemaRelation(
        source_class=record["source_class"],
        relation_name=record["relation_name"],
        target_class=record["target_class"],
        status=record.get("status", "draft"),
        description=record.get("description") or "",
    )


def map_to_triple_dict(record: Dict[str, Any]) -> dict:
    return {
        "subject_name": record["subject_name"],
        "subject_type": record["subject_type"],
        "predicate": record["predicate"],
        "object_name": record["object_name"],
        "object_type": record["object_type"],
    }
