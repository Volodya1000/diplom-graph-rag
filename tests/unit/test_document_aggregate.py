"""
Unit: DocumentAggregate — построение рёбер документа.

Поведение:
  - HAS_CHUNK от документа к каждому чанку
  - NEXT_CHUNK / PREV_CHUNK между соседними чанками
  - Один чанк — нет NEXT/PREV
"""

from src.domain.graph_components.nodes import DocumentNode, ChunkNode
from src.domain.graph_components.edges import GraphRelationType
from src.domain.aggregates.document_agregate import DocumentAggregate


class TestDocumentAggregateEdges:
    def test_single_chunk_produces_one_has_chunk_edge(self):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        chunks = [
            ChunkNode(chunk_id="c1", doc_id="doc-1", chunk_index=0, text="text"),
        ]
        agg = DocumentAggregate(document=doc, chunks=chunks)

        edges = agg.build_edges()

        assert len(edges) == 1
        assert edges[0].relation_type == GraphRelationType.HAS_CHUNK
        assert edges[0].source_id == "doc-1"
        assert edges[0].target_id == "c1"

    def test_two_chunks_produce_has_chunk_and_navigation_edges(self):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        chunks = [
            ChunkNode(chunk_id="c1", doc_id="doc-1", chunk_index=0, text="first"),
            ChunkNode(chunk_id="c2", doc_id="doc-1", chunk_index=1, text="second"),
        ]
        agg = DocumentAggregate(document=doc, chunks=chunks)

        edges = agg.build_edges()

        # 2 HAS_CHUNK + 1 NEXT + 1 PREV = 4
        assert len(edges) == 4

        rel_types = [e.relation_type for e in edges]
        assert rel_types.count(GraphRelationType.HAS_CHUNK) == 2
        assert rel_types.count(GraphRelationType.NEXT_CHUNK) == 1
        assert rel_types.count(GraphRelationType.PREV_CHUNK) == 1

    def test_three_chunks_produce_correct_navigation_chain(self):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        chunks = [
            ChunkNode(chunk_id="c1", doc_id="doc-1", chunk_index=0, text="a"),
            ChunkNode(chunk_id="c2", doc_id="doc-1", chunk_index=1, text="b"),
            ChunkNode(chunk_id="c3", doc_id="doc-1", chunk_index=2, text="c"),
        ]
        agg = DocumentAggregate(document=doc, chunks=chunks)

        edges = agg.build_edges()

        # 3 HAS_CHUNK + 2 NEXT + 2 PREV = 7
        assert len(edges) == 7

        next_edges = [
            e for e in edges if e.relation_type == GraphRelationType.NEXT_CHUNK
        ]
        assert len(next_edges) == 2
        assert next_edges[0].source_id == "c1"
        assert next_edges[0].target_id == "c2"
        assert next_edges[1].source_id == "c2"
        assert next_edges[1].target_id == "c3"

    def test_empty_chunks_produce_no_edges(self):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        agg = DocumentAggregate(document=doc, chunks=[])

        edges = agg.build_edges()

        assert edges == []
