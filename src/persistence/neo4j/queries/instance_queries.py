from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import re
from .base import Neo4jQuery


_SAFE_REL = re.compile(r"[^A-Za-z0-9_]")


@dataclass
class SaveInstanceQuery(Neo4jQuery):
    instance_id: str
    props: Dict[str, Any]
    embedding: Optional[List[float]] = None

    def get_query(self) -> str:
        if self.embedding is not None:
            return """
                MERGE (i:Instance {instance_id: $instance_id})
                SET i += $props
                WITH i
                CALL db.create.setNodeVectorProperty(i, 'embedding', $embedding)
            """
        return """
            MERGE (i:Instance {instance_id: $instance_id})
            SET i += $props
        """

    def get_params(self) -> Dict[str, Any]:
        p: Dict[str, Any] = {"instance_id": self.instance_id, "props": self.props}
        if self.embedding is not None:
            p["embedding"] = self.embedding
        return p


@dataclass
class FindCandidatesByVectorQuery(Neo4jQuery):
    embedding: List[float]
    limit: int = 10
    threshold: Optional[float] = None

    def get_query(self) -> str:
        return """
            CALL db.index.vector.queryNodes(
                'instance_embedding', $limit, $embedding
            )
            YIELD node AS n, score
            WHERE score >= $threshold
            RETURN n.instance_id AS instance_id,
                   n.name AS name,
                   n.class_name AS class_name,
                   n.chunk_id AS chunk_id,
                   score
            ORDER BY score DESC
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "embedding": self.embedding,
            "limit": self.limit,
            "threshold": self.threshold,
        }


@dataclass
class SaveInstanceRelationQuery(Neo4jQuery):
    source_id: str
    target_id: str
    relation_name: str
    chunk_id: str

    def get_query(self) -> str:
        safe_name = _SAFE_REL.sub("_", self.relation_name).upper() or "RELATED_TO"
        return f"""
            MATCH (src:Instance {{instance_id: $source_id}})
            MATCH (tgt:Instance {{instance_id: $target_id}})
            MERGE (src)-[r:{safe_name}]->(tgt)
            SET r.chunk_id = $chunk_id
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "chunk_id": self.chunk_id,
        }


@dataclass
class GetInstancesByChunkQuery(Neo4jQuery):
    chunk_id: str

    def get_query(self) -> str:
        return """
            MATCH (i:Instance)-[:MENTIONED_IN]->(c:Chunk {chunk_id: $chunk_id})
            RETURN i.instance_id AS instance_id,
                   i.name AS name,
                   i.class_name AS class_name,
                   i.chunk_id AS chunk_id,
                   i.embedding AS embedding
        """

    def get_params(self) -> Dict[str, Any]:
        return {"chunk_id": self.chunk_id}


@dataclass
class GetTriplesByChunkQuery(Neo4jQuery):
    chunk_id: str

    def get_query(self) -> str:
        return """
            MATCH (src:Instance)-[r]->(tgt:Instance)
            WHERE r.chunk_id = $chunk_id
            RETURN src.name AS subject_name,
                   src.class_name AS subject_type,
                   type(r) AS predicate,
                   tgt.name AS object_name,
                   tgt.class_name AS object_type
        """

    def get_params(self) -> Dict[str, Any]:
        return {"chunk_id": self.chunk_id}


@dataclass
class GetInstancesByDocumentQuery(Neo4jQuery):
    doc_id: str

    def get_query(self) -> str:
        return """
            MATCH (c:Chunk {doc_id: $doc_id})
            MATCH (i:Instance)-[:MENTIONED_IN]->(c)
            RETURN DISTINCT
                   i.instance_id AS instance_id,
                   i.name AS name,
                   i.class_name AS class_name,
                   i.chunk_id AS chunk_id,
                   i.aliases AS aliases,
                   i.embedding AS embedding
        """

    def get_params(self) -> Dict[str, Any]:
        return {"doc_id": self.doc_id}


@dataclass
class GetAllInstancesQuery(Neo4jQuery):
    def get_query(self) -> str:
        return """
            MATCH (i:Instance)
            RETURN i.instance_id AS instance_id,
                   i.name AS name,
                   i.class_name AS class_name,
                   i.chunk_id AS chunk_id,
                   i.aliases AS aliases,
                   i.embedding AS embedding
        """

    def get_params(self) -> Dict[str, Any]:
        return {}


# ==================== MERGE QUERIES ====================
@dataclass
class TransferAliasIncomingEdgesQuery(Neo4jQuery):
    alias_ids: List[str]
    canonical_id: str

    def get_query(self) -> str:
        return """
            UNWIND $alias_ids AS aid
            MATCH (alias:Instance {instance_id: aid})<-[r]-(source)
            WHERE source.instance_id <> $canonical_id
            WITH source, alias, r, type(r) AS rel_type, properties(r) AS props
            MATCH (canonical:Instance {instance_id: $canonical_id})
            CALL apoc.create.relationship(source, rel_type, props, canonical)
            YIELD rel
            DELETE r
        """

    def get_params(self) -> Dict[str, Any]:
        return {"alias_ids": self.alias_ids, "canonical_id": self.canonical_id}


@dataclass
class TransferAliasOutgoingEdgesQuery(Neo4jQuery):
    alias_ids: List[str]
    canonical_id: str

    def get_query(self) -> str:
        return """
            UNWIND $alias_ids AS aid
            MATCH (alias:Instance {instance_id: aid})-[r]->(target)
            WHERE target.instance_id <> $canonical_id
            WITH alias, target, r, type(r) AS rel_type, properties(r) AS props
            MATCH (canonical:Instance {instance_id: $canonical_id})
            CALL apoc.create.relationship(canonical, rel_type, props, target)
            YIELD rel
            DELETE r
        """

    def get_params(self) -> Dict[str, Any]:
        return {"alias_ids": self.alias_ids, "canonical_id": self.canonical_id}


@dataclass
class TransferAliasMentionedInQuery(Neo4jQuery):
    alias_ids: List[str]
    canonical_id: str

    def get_query(self) -> str:
        return """
            UNWIND $alias_ids AS aid
            MATCH (alias:Instance {instance_id: aid})-[r:MENTIONED_IN]->(c:Chunk)
            MATCH (canonical:Instance {instance_id: $canonical_id})
            MERGE (canonical)-[:MENTIONED_IN]->(c)
            DELETE r
        """

    def get_params(self) -> Dict[str, Any]:
        return {"alias_ids": self.alias_ids, "canonical_id": self.canonical_id}


@dataclass
class UpdateCanonicalInstanceQuery(Neo4jQuery):
    canonical_id: str
    canonical_name: str
    aliases: List[str]

    def get_query(self) -> str:
        return """
            MATCH (c:Instance {instance_id: $canonical_id})
            SET c.name = $canonical_name,
                c.aliases = $aliases
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
        }


@dataclass
class DeleteAliasInstancesQuery(Neo4jQuery):
    alias_ids: List[str]

    def get_query(self) -> str:
        return """
            UNWIND $alias_ids AS aid
            MATCH (alias:Instance {instance_id: aid})
            DETACH DELETE alias
        """

    def get_params(self) -> Dict[str, Any]:
        return {"alias_ids": self.alias_ids}
