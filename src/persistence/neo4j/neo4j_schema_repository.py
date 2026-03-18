"""T-Box: классы онтологии, отношения, индексы."""

import logging
from typing import List, Dict

from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.ontology.shema import SchemaClass, SchemaRelation
from src.persistence.neo4j.base_repository import Neo4jBaseRepository
from src.persistence.neo4j.mappers.node_mappers import (
    map_to_schema_class,
    map_to_schema_relation,
)

logger = logging.getLogger(__name__)


class Neo4jSchemaRepository(Neo4jBaseRepository, ISchemaRepository):

    # ==================== ИНДЕКСЫ ====================

    async def ensure_indexes(self) -> None:
        dim = self._settings.embedding_dim
        async with self._sm.session() as s:
            await s.run(f"""
                CREATE VECTOR INDEX instance_embedding IF NOT EXISTS
                FOR (n:Instance) ON (n.embedding)
                OPTIONS {{indexConfig: {{
                  `vector.dimensions`: {dim},
                  `vector.similarity_function`: 'cosine'
                }}}}
            """)
            await s.run(f"""
                CREATE VECTOR INDEX chunk_embedding IF NOT EXISTS
                FOR (c:Chunk) ON (c.embedding)
                OPTIONS {{indexConfig: {{
                  `vector.dimensions`: {dim},
                  `vector.similarity_function`: 'cosine'
                }}}}
            """)
            await s.run("""
                CREATE INDEX instance_name_idx IF NOT EXISTS
                FOR (i:Instance) ON (i.name)
            """)
            await s.run("""
                CREATE INDEX schema_class_name_idx IF NOT EXISTS
                FOR (c:SchemaClass) ON (c.name)
            """)
        logger.info(f"📐 Индексы обеспечены (embedding_dim={dim})")

    # ==================== КЛАССЫ ====================

    async def get_tbox_classes(self) -> List[SchemaClass]:
        data = await self._fetch_all("""
            MATCH (c:SchemaClass)
            RETURN c.name        AS name,
                   c.status      AS status,
                   c.description AS description,
                   c.parent      AS parent
        """)
        return [map_to_schema_class(r) for r in data]

    async def save_tbox_classes(self, classes: List[SchemaClass]) -> None:
        if not classes:
            return

        batch = [
            {
                "name": c.name,
                "status": c.status.value,
                "description": c.description,
                "parent": c.parent,
            }
            for c in classes
        ]

        async with self._sm.session() as s:
            await s.run("""
                UNWIND $batch AS row
                MERGE (c:SchemaClass {name: row.name})
                ON CREATE SET c.status      = row.status,
                              c.description = row.description,
                              c.parent      = row.parent
                ON MATCH  SET c.description = row.description,
                              c.parent      = row.parent
            """, batch=batch)

            await s.run("""
                UNWIND $batch AS row
                WITH row WHERE row.parent IS NOT NULL
                MATCH (child:SchemaClass  {name: row.name})
                MATCH (parent:SchemaClass {name: row.parent})
                MERGE (child)-[:SUBCLASS_OF]->(parent)
            """, batch=batch)

            await s.run("""
                MATCH (child:SchemaClass)
                WHERE child.parent IS NOT NULL
                  AND NOT (child)-[:SUBCLASS_OF]->()
                MATCH (parent:SchemaClass {name: child.parent})
                MERGE (child)-[:SUBCLASS_OF]->(parent)
            """)

    # ==================== ОТНОШЕНИЯ ====================

    async def get_schema_relations(self) -> List[SchemaRelation]:
        data = await self._fetch_all("""
            MATCH (src:SchemaClass)-[r:ALLOWED_RELATION]->(tgt:SchemaClass)
            RETURN src.name      AS source_class,
                   r.name        AS relation_name,
                   tgt.name      AS target_class,
                   r.status      AS status,
                   r.description AS description
        """)
        return [map_to_schema_relation(r) for r in data]

    async def save_schema_relations(
        self, relations: List[SchemaRelation],
    ) -> None:
        if not relations:
            return
        batch = [
            {
                "source_class": r.source_class,
                "relation_name": r.relation_name,
                "target_class": r.target_class,
                "status": r.status.value,
                "description": r.description,
            }
            for r in relations
        ]
        await self._execute("""
            UNWIND $batch AS row
            MATCH (src:SchemaClass {name: row.source_class})
            MATCH (tgt:SchemaClass {name: row.target_class})
            MERGE (src)-[r:ALLOWED_RELATION {name: row.relation_name}]->(tgt)
            ON CREATE SET r.status      = row.status,
                          r.description = row.description
            ON MATCH  SET r.description = row.description
        """, {"batch": batch})

    async def get_class_usage_counts(self) -> Dict[str, int]:
        data = await self._fetch_all("""
            MATCH (sc:SchemaClass)
            OPTIONAL MATCH (i:Instance)-[:INSTANCE_OF]->(sc)
            RETURN sc.name AS name, COUNT(i) AS usage
        """)
        return {r["name"]: r["usage"] for r in data}