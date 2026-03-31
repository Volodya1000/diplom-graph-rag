"""Unit: ContextBuilder."""

import pytest
from src.application.services.context_builder import ContextBuilder
from src.domain.value_objects.search_context import (
    RetrievalResult,
    RetrievedChunk,
    RetrievedTriple,
    RetrievedCommunity,
)


@pytest.fixture
def builder() -> ContextBuilder:
    return ContextBuilder(max_context_chars=5000)


class TestContextBuilderChunks:
    def test_chunks_sorted_by_score_descending(self, builder):
        result = RetrievalResult(
            chunks=[
                RetrievedChunk(
                    chunk_id="c1", text="Low", score=0.5, source_filename="f.pdf"
                ),
                RetrievedChunk(
                    chunk_id="c2", text="High", score=0.9, source_filename="f.pdf"
                ),
            ]
        )
        context = builder.build(result)
        high_pos = context.find("High")
        low_pos = context.find("Low")
        assert high_pos < low_pos

    def test_formatting_includes_filename_and_pages(self, builder):
        result = RetrievalResult(
            chunks=[
                RetrievedChunk(
                    chunk_id="c1",
                    text="Текст отчета",
                    score=0.9,
                    source_filename="Отчет.pdf",
                    chunk_index=1,
                    start_page=10,
                    end_page=11,
                )
            ]
        )
        context = builder.build(result)
        assert "[Документ: Отчет.pdf, Стр. 10-11]" in context


class TestContextBuilderTriples:
    def test_triples_formatted_with_arrow(self, builder):
        result = RetrievalResult(
            triples=[
                RetrievedTriple(
                    subject="Колобок",
                    subject_type="Product",
                    predicate="CREATED",
                    object="Старуха",
                    object_type="Person",
                ),
            ]
        )
        context = builder.build(result)
        assert "Колобок" in context
        assert "CREATED" in context
        assert "Старуха" in context


class TestContextBuilderCommunities:
    def test_community_summaries_included(self, builder):
        result = RetrievalResult(
            communities=[
                RetrievedCommunity(
                    community_id=1,
                    summary="Сказка про Колобка",
                    key_entities=["Колобок", "Заяц"],
                    relevance_score=0.8,
                ),
            ]
        )
        context = builder.build(result)
        assert "Сказка про Колобка" in context
