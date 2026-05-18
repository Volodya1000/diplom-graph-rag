"""Integration: Neo4jDocumentRepository — документы и чанки."""

import pytest

from src.domain.models.nodes import ChunkNode, DocumentNode, InstanceNode

pytestmark = pytest.mark.integration


class TestDocumentCRUD:
    async def test_save_and_retrieve_document_by_filename(self, doc_repo):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")

        await doc_repo.save_document(doc)

        result = await doc_repo.get_document_by_filename("test.pdf")
        assert len(result) == 1
        assert result[0].doc_id == "doc-1"
        assert result[0].filename == "test.pdf"

    async def test_nonexistent_filename_returns_empty(self, doc_repo):
        result = await doc_repo.get_document_by_filename("ghost.pdf")

        assert result == []

    async def test_document_stats_counts_triples_via_mentioned_in(
        self, doc_repo, schema_repo, instance_repo, edge_repo
    ):
        await schema_repo.ensure_indexes()

        # Создаем документ и чанк
        doc = DocumentNode(doc_id="doc_stat", filename="stat.pdf")
        await doc_repo.save_document(doc)
        chunk = ChunkNode(chunk_id="c_stat", doc_id="doc_stat", chunk_index=0, text="hello")
        await doc_repo.save_chunk(chunk)

        # Создаем инстансы
        inst1 = InstanceNode(instance_id="i1", name="A", class_name="Person", chunk_id="c_stat")
        inst2 = InstanceNode(instance_id="i2", name="B", class_name="Person", chunk_id="c_stat")
        await instance_repo.save_instance(inst1)
        await instance_repo.save_instance(inst2)

        # Привязываем инстансы к чанку
        from src.domain.models.edges import GraphEdge, GraphRelationType

        await edge_repo.save_edges(
            [
                GraphEdge(relation_type=GraphRelationType.MENTIONED_IN, source_id="i1", target_id="c_stat"),
                GraphEdge(relation_type=GraphRelationType.MENTIONED_IN, source_id="i2", target_id="c_stat"),
            ]
        )

        # Создаем триплет
        async with doc_repo._sm.session() as s:
            await s.run(
                "MATCH (a:Instance {instance_id: 'i1'}), (b:Instance {instance_id: 'i2'}) MERGE (a)-[:KNOWS]->(b)"
            )

        # Проверяем статистику
        stats = await doc_repo.get_document_stats("doc_stat")

        assert stats is not None
        assert stats.chunks_count == 1
        assert stats.entities_count == 2
        assert stats.triples_count == 1


class TestChunkCRUD:
    async def test_save_and_retrieve_chunks_ordered_by_index(self, doc_repo):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        await doc_repo.save_document(doc)
        chunks = [
            ChunkNode(
                chunk_id=f"c{i}",
                doc_id="doc-1",
                chunk_index=i,
                text=f"text {i}",
            )
            for i in [2, 0, 1]  # намеренно не по порядку
        ]
        for c in chunks:
            await doc_repo.save_chunk(c)

        result = await doc_repo.get_chunks_by_document("doc-1")

        assert len(result) == 3
        assert [c.chunk_index for c in result] == [0, 1, 2]

    async def test_chunk_with_embedding_is_saved(self, doc_repo, schema_repo):
        await schema_repo.ensure_indexes()
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        await doc_repo.save_document(doc)
        chunk = ChunkNode(
            chunk_id="c1",
            doc_id="doc-1",
            chunk_index=0,
            text="hello",
            embedding=[0.1] * 384,
        )

        await doc_repo.save_chunk(chunk)

        result = await doc_repo.get_chunks_by_document("doc-1")
        assert len(result) == 1
        assert result[0].text == "hello"

    async def test_chunks_for_nonexistent_doc_returns_empty(self, doc_repo):
        result = await doc_repo.get_chunks_by_document("ghost-id")

        assert result == []
