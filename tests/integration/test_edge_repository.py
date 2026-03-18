"""
Integration: Neo4jEdgeRepository — структурные рёбра графа.
"""

import pytest
from src.domain.graph_components.nodes import DocumentNode, ChunkNode
from src.domain.graph_components.edges import GraphEdge, GraphRelationType


pytestmark = pytest.mark.integration


class TestEdgeCreation:

    async def test_has_chunk_edge_created(self, edge_repo, doc_repo):
        doc = DocumentNode(doc_id="d1", filename="t.pdf")
        await doc_repo.save_document(doc)
        chunk = ChunkNode(
            chunk_id="c1", doc_id="d1", chunk_index=0, text="text",
        )
        await doc_repo.save_chunk(chunk)

        edges = [
            GraphEdge(
                relation_type=GraphRelationType.HAS_CHUNK,
                source_id="d1", target_id="c1",
            ),
        ]
        await edge_repo.save_edges(edges)

        # Проверяем отдельным запросом
        from src.persistence.neo4j.base_repository import Neo4jBaseRepository
        data = await edge_repo._fetch_all("""
            MATCH (d:Document {doc_id: 'd1'})-[:HAS_CHUNK]->(c:Chunk {chunk_id: 'c1'})
            RETURN d.doc_id AS doc_id, c.chunk_id AS chunk_id
        """)
        assert len(data) == 1
        assert data[0]["doc_id"] == "d1"
        assert data[0]["chunk_id"] == "c1"

    async def test_empty_edges_does_nothing(self, edge_repo):
        await edge_repo.save_edges([])

        # Не должен падать