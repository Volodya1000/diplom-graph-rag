import pytest
from src.application.services.context_builder import ContextBuilder
from src.domain.models.search import RetrievalResult, RetrievedChunk
from src.config.rag_settings import RAGSettings

@pytest.fixture
def builder() -> ContextBuilder:
    return ContextBuilder(settings=RAGSettings(max_context_chars=5000))

class TestContextBuilderChunks:
    def test_chunks_sorted_by_score_descending(self, builder):
        result = RetrievalResult(chunks=[
            RetrievedChunk(chunk_id="c1", text="Low", score=0.5, source_filename="f.pdf"),
            RetrievedChunk(chunk_id="c2", text="High", score=0.9, source_filename="f.pdf"),
        ])
        context = builder.build(result)
        assert context.find("High") < context.find("Low")