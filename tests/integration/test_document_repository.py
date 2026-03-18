"""
Integration: Neo4jDocumentRepository — документы и чанки.
"""

import pytest
from src.domain.graph_components.nodes import DocumentNode, ChunkNode


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


class TestChunkCRUD:

    async def test_save_and_retrieve_chunks_ordered_by_index(self, doc_repo):
        doc = DocumentNode(doc_id="doc-1", filename="test.pdf")
        await doc_repo.save_document(doc)
        chunks = [
            ChunkNode(
                chunk_id=f"c{i}", doc_id="doc-1",
                chunk_index=i, text=f"text {i}",
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
            chunk_id="c1", doc_id="doc-1", chunk_index=0,
            text="hello", embedding=[0.1] * 384,
        )

        await doc_repo.save_chunk(chunk)

        result = await doc_repo.get_chunks_by_document("doc-1")
        assert len(result) == 1
        assert result[0].text == "hello"

    async def test_chunks_for_nonexistent_doc_returns_empty(self, doc_repo):
        result = await doc_repo.get_chunks_by_document("ghost-id")

        assert result == []