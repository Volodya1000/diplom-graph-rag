from dataclasses import dataclass
from typing import Dict, Any
from .base import Neo4jQuery


@dataclass
class SaveEdgeQuery(Neo4jQuery):
    relation_type: str
    source_id: str
    target_id: str

    def get_query(self) -> str:
        return f"""
            MATCH (source)
            WHERE (source:Document AND source.doc_id = $source_id)
               OR (source:Chunk AND source.chunk_id = $source_id)
               OR (source:Instance AND source.instance_id = $source_id)
            MATCH (target)
            WHERE (target:Chunk AND target.chunk_id = $target_id)
               OR (target:SchemaClass AND target.name = $target_id)
            MERGE (source)-[:{self.relation_type}]->(target)
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
        }
