from dataclasses import dataclass
from typing import Dict, Any, List
from .base import Neo4jQuery
from src.domain.ontology.schema import SchemaClass, SchemaRelation
from src.persistence.neo4j.mappers.node_mappers import (
    map_to_schema_class,
    map_to_schema_relation,
)


@dataclass
class CreateInstanceEmbeddingIndexQuery(Neo4jQuery[Any]):
    dim: int

    def get_query(self) -> str:
        return f"""
            CREATE VECTOR INDEX instance_embedding IF NOT EXISTS
            FOR (n:Instance) ON (n.embedding)
            OPTIONS {{indexConfig: {{
              `vector.dimensions`: {self.dim},
              `vector.similarity_function`: 'cosine'
            }}}}
        """

    def get_params(self) -> Dict[str, Any]:
        return {}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class CreateChunkEmbeddingIndexQuery(Neo4jQuery[Any]):
    dim: int

    def get_query(self) -> str:
        return f"""
            CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
            FOR (c:Chunk) ON (c.embedding)
            OPTIONS {{indexConfig: {{
              `vector.dimensions`: {self.dim},
              `vector.similarity_function`: 'cosine'
            }}}}
        """

    def get_params(self) -> Dict[str, Any]:
        return {}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class CreateInstanceNameIndexQuery(Neo4jQuery[Any]):
    def get_query(self) -> str:
        return (
            "CREATE INDEX instance_name_idx IF NOT EXISTS FOR (i:Instance) ON (i.name)"
        )

    def get_params(self) -> Dict[str, Any]:
        return {}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class CreateSchemaClassNameIndexQuery(Neo4jQuery[Any]):
    def get_query(self) -> str:
        return "CREATE INDEX schema_class_name_idx IF NOT EXISTS FOR (c:SchemaClass) ON (c.name)"

    def get_params(self) -> Dict[str, Any]:
        return {}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class GetTboxClassesQuery(Neo4jQuery[SchemaClass]):
    def get_query(self) -> str:
        return """
            MATCH (c:SchemaClass)
            RETURN c.name AS name, c.status AS status,
                   c.description AS description, c.parent AS parent
        """

    def get_params(self) -> Dict[str, Any]:
        return {}

    def map_record(self, record: Dict[str, Any]) -> SchemaClass:
        return map_to_schema_class(record)


@dataclass
class SaveTboxClassesQuery(Neo4jQuery[Any]):
    batch: List[Dict[str, Any]]

    def get_query(self) -> str:
        return """
            UNWIND $batch AS row
            MERGE (c:SchemaClass {name: row.name})
            ON CREATE SET c.status = row.status, c.description = row.description, c.parent = row.parent
            ON MATCH SET c.description = row.description, c.parent = row.parent
        """

    def get_params(self) -> Dict[str, Any]:
        return {"batch": self.batch}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class CreateSubclassOfEdgesQuery(Neo4jQuery[Any]):
    batch: List[Dict[str, Any]]

    def get_query(self) -> str:
        return """
            UNWIND $batch AS row
            WITH row WHERE row.parent IS NOT NULL
            MATCH (child:SchemaClass {name: row.name})
            MATCH (parent:SchemaClass {name: row.parent})
            MERGE (child)-[:SUBCLASS_OF]->(parent)
        """

    def get_params(self) -> Dict[str, Any]:
        return {"batch": self.batch}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class GetSchemaRelationsQuery(Neo4jQuery[SchemaRelation]):
    def get_query(self) -> str:
        return """
            MATCH (src:SchemaClass)-[r:ALLOWED_RELATION]->(tgt:SchemaClass)
            RETURN src.name AS source_class, r.name AS relation_name,
                   tgt.name AS target_class, r.status AS status, r.description AS description
        """

    def get_params(self) -> Dict[str, Any]:
        return {}

    def map_record(self, record: Dict[str, Any]) -> SchemaRelation:
        return map_to_schema_relation(record)


@dataclass
class SaveSchemaRelationsQuery(Neo4jQuery[Any]):
    batch: List[Dict[str, Any]]

    def get_query(self) -> str:
        return """
            UNWIND $batch AS row
            MATCH (src:SchemaClass {name: row.source_class})
            MATCH (tgt:SchemaClass {name: row.target_class})
            MERGE (src)-[r:ALLOWED_RELATION {name: row.relation_name}]->(tgt)
            ON CREATE SET r.status = row.status, r.description = row.description
            ON MATCH SET r.description = row.description
        """

    def get_params(self) -> Dict[str, Any]:
        return {"batch": self.batch}

    def map_record(self, record: Dict[str, Any]) -> Any:
        return None


@dataclass
class GetClassUsageCountsQuery(Neo4jQuery[Dict[str, Any]]):
    def get_query(self) -> str:
        return """
            MATCH (sc:SchemaClass)
            OPTIONAL MATCH (i:Instance)-[:INSTANCE_OF]->(sc)
            RETURN sc.name AS name, COUNT(i) AS usage
        """

    def get_params(self) -> Dict[str, Any]:
        return {}

    def map_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return {"name": record["name"], "usage": record["usage"]}
