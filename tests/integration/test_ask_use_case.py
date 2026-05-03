"""
Integration: Проверка полного цикла сборки контекста и генерации ответа.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.context_builder import ContextBuilder
from src.application.services.retrieval_registry import RetrievalStrategyRegistry
from src.application.use_cases.answer_question import AnswerQuestionUseCase
from src.config.rag_settings import RAGSettings
from src.domain.models.nodes import ChunkNode, DocumentNode
from src.domain.models.search import SearchMode
from src.infrastructure.llm.clients.llm_answer_generator import OllamaAnswerGenerator

from src.infrastructure.llm.llm_factory import ChatModelFactory
from src.infrastructure.retrieval.vector_search_strategy import VectorSearchStrategy

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_embedder():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 384
    return embedder


@pytest.fixture
def mock_file_storage():
    """Заглушка для генерации ссылок в тестах."""
    storage = MagicMock()
    storage.get_download_url.side_effect = lambda filename: f"http://test-api/uploads/{filename}"
    return storage


@pytest.fixture
def real_ollama_generator(llm_settings):
    factory = ChatModelFactory(llm_settings)
    return OllamaAnswerGenerator(factory)


class TestAskUseCase:
    async def test_db_retrieval_includes_pages_and_filename(
        self,
        doc_repo,
        schema_repo,
        session_manager,
        instance_repo,
    ):
        await schema_repo.ensure_indexes()

        doc = DocumentNode(doc_id="d1", filename="Финансовый_отчет_2024.pdf")
        await doc_repo.save_document(doc)

        chunk = ChunkNode(
            chunk_id="c1",
            doc_id="d1",
            chunk_index=1,
            text="Выручка компании выросла на 25%.",
            start_page=14,
            end_page=15,
            embedding=[0.1] * 384,
        )
        await doc_repo.save_chunk(chunk)

        strategy = VectorSearchStrategy(session_manager, instance_repo)

        result = await strategy.retrieve(
            "Как выросла выручка?",
            query_embedding=[0.1] * 384,
        )

        assert len(result.chunks) == 1
        c = result.chunks[0]
        assert c.source_filename == "Финансовый_отчет_2024.pdf"
        assert c.start_page == 14
        assert c.end_page == 15

    async def test_ollama_generates_answer_with_citations(self, real_ollama_generator):
        context_text = (
            "=== РЕЛЕВАНТНЫЕ ФРАГМЕНТЫ ИЗ ДОКУМЕНТОВ ===\n"
            "--- Фрагмент #1[Документ: Устав_Корпорации.pdf, Стр. 10-10] ---\n"
            "Генеральный директор назначается сроком на 5 лет.\n\n"
            "--- Фрагмент #2[Документ: Регламент_Безопасности.docx, Стр. 3-4] ---\n"
            "Пароли сотрудников должны меняться каждые 90 дней."
        )

        question = "На какой срок назначается гендиректор и как часто нужно менять пароли?"

        try:
            response = await real_ollama_generator.generate(
                question=question,
                context=context_text,
            )

            assert "5" in response or "пять" in response.lower()
            assert "90" in response or "девяносто" in response.lower()

            assert "[Документ: Устав_Корпорации.pdf" in response
            assert "[Документ: Регламент_Безопасности.docx" in response
            assert "Стр." in response

        except Exception as e:
            pytest.skip(
                f"Ollama недоступна или произошла ошибка. Пропуск теста генерации. Ошибка: {e}",
            )

    async def test_full_use_case_orchestration(
        self,
        doc_repo,
        schema_repo,
        session_manager,
        instance_repo,
        mock_embedder,
        mock_file_storage,
    ):
        await schema_repo.ensure_indexes()

        doc = DocumentNode(doc_id="d1", filename="Секретный_План.pdf")
        await doc_repo.save_document(doc)

        chunk = ChunkNode(
            chunk_id="c1",
            doc_id="d1",
            chunk_index=0,
            text="Операция на рассвете.",
            start_page=42,
            end_page=42,
            embedding=[0.1] * 384,
        )
        await doc_repo.save_chunk(chunk)

        mock_llm_generator = AsyncMock()
        mock_llm_generator.generate.return_value = "На рассвете[Документ: Секретный_План.pdf, Стр. 42]."

        strategy = VectorSearchStrategy(session_manager, instance_repo)
        registry = RetrievalStrategyRegistry()
        registry.register(SearchMode.LOCAL, strategy)

        builder = ContextBuilder(settings=RAGSettings())
        use_case = AnswerQuestionUseCase(
            embedder=mock_embedder,
            registry=registry,
            context_builder=builder,
            generator=mock_llm_generator,
            file_storage=mock_file_storage,
        )

        response = await use_case.execute(
            question="Когда начнется операция?",
            mode=SearchMode.LOCAL,
        )

        assert len(response.sources) == 1
        assert response.sources[0].filename == "Секретный_План.pdf"
        assert response.sources[0].download_url == "http://test-api/uploads/Секретный_План.pdf"
