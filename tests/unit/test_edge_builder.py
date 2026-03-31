"""Unit: GraphEdgeBuilder — построение рёбер документа и сущностей."""

from src.domain.models.nodes import DocumentNode, ChunkNode, InstanceNode
from src.domain.models.edges import GraphRelationType
from src.domain.services.builders.edge_builder import GraphEdgeBuilder


class TestDocumentEdges:
    def test_single_chunk_produces_one_has_chunk_edge(self):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        chunks = [ChunkNode(chunk_id="c1", doc_id="doc-1", chunk_index=0, text="text")]
        edges = GraphEdgeBuilder.build_document_edges(document=doc, chunks=chunks)
        assert len(edges) == 1
        assert edges[0].relation_type == GraphRelationType.HAS_CHUNK

    def test_two_chunks_produce_has_chunk_and_navigation_edges(self):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        chunks = [
            ChunkNode(chunk_id="c1", doc_id="doc-1", chunk_index=0, text="first"),
            ChunkNode(chunk_id="c2", doc_id="doc-1", chunk_index=1, text="second"),
        ]
        edges = GraphEdgeBuilder.build_document_edges(document=doc, chunks=chunks)
        assert len(edges) == 4
        rel_types = [e.relation_type for e in edges]
        assert rel_types.count(GraphRelationType.HAS_CHUNK) == 2
        assert rel_types.count(GraphRelationType.NEXT_CHUNK) == 1
        assert rel_types.count(GraphRelationType.PREV_CHUNK) == 1


class TestInstanceEdges:
    def test_produces_exactly_two_edges(self):
        inst = InstanceNode(
            instance_id="i1", name="Колобок", class_name="Product", chunk_id="c1"
        )
        edges = GraphEdgeBuilder.build_instance_edges(instance=inst)
        assert len(edges) == 2
        instance_of = [
            e for e in edges if e.relation_type == GraphRelationType.INSTANCE_OF
        ]
        assert instance_of[0].target_id == "Product"
