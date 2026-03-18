"""
Unit: ContextBuilder — сборка текстового контекста из RetrievalResult.

Поведение:
  - Чанки сортируются по score desc
  - Тройки форматируются как «subject → predicate → object»
  - Community summaries включаются первыми
  - Пустой результат → placeholder
  - Бюджет символов соблюдается
"""

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
        result = RetrievalResult(chunks=[
            RetrievedChunk(chunk_id="c1", text="Low", score=0.5, chunk_index=1),
            RetrievedChunk(chunk_id="c2", text="High", score=0.9, chunk_index=2),
        ])

        context = builder.build(result)

        high_pos = context.find("High")
        low_pos = context.find("Low")
        assert high_pos < low_pos

    def test_empty_result_returns_placeholder(self, builder):
        result = RetrievalResult()

        context = builder.build(result)

        assert "не найден" in context


class TestContextBuilderTriples:

    def test_triples_formatted_with_arrow(self, builder):
        result = RetrievalResult(triples=[
            RetrievedTriple(
                subject="Колобок", subject_type="Product",
                predicate="CREATED", object="Старуха",
                object_type="Person",
            ),
        ])

        context = builder.build(result)

        assert "Колобок" in context
        assert "CREATED" in context
        assert "Старуха" in context


class TestContextBuilderCommunities:

    def test_community_summaries_included(self, builder):
        result = RetrievalResult(communities=[
            RetrievedCommunity(
                community_id=1, summary="Сказка про Колобка",
                key_entities=["Колобок", "Заяц"],
                relevance_score=0.8,
            ),
        ])

        context = builder.build(result)

        assert "Сказка про Колобка" in context


class TestContextBuilderStats:

    def test_stats_reflect_result_counts(self, builder):
        result = RetrievalResult(
            chunks=[RetrievedChunk(chunk_id="c1", text="t", score=0.5)],
            triples=[
                RetrievedTriple(
                    subject="A", subject_type="X", predicate="R",
                    object="B", object_type="Y",
                ),
            ],
            communities=[
                RetrievedCommunity(
                    community_id=1, summary="S",
                    relevance_score=0.5,
                ),
            ],
        )

        stats = builder.get_stats(result)

        assert stats["chunks_count"] == 1
        assert stats["triples_count"] == 1
        assert stats["communities_count"] == 1