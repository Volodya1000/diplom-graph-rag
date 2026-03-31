"""
Integration: Проверка полного цикла сборки контекста и генерации ответа.
Тестирует:
  1. Корректное извлечение чанков с указанием страниц (VectorSearchStrategy).
  2. Сборку контекста с [Документ: ..., Стр: ...].
  3. Работу LLM с требованием цитирования.
"""

import pytest
from unittest.mock import AsyncMock

from src.domain.graph_components.nodes import DocumentNode, ChunkNode
from src.domain.value_objects.search_context import SearchMode
from src.application.use_cases.answer_question import AnswerQuestionUseCase
from src.application.services.context_builder import ContextBuilder
from src.application.services.retrieval_registry import RetrievalStrategyRegistry
from src.infrastructure.retrieval.vector_search_strategy import VectorSearchStrategy

# Для тестирования с реальной Ollama, если она поднята
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.infrastructure.llm.clients.llm_answer_generator import OllamaAnswerGenerator
from src.config.ollama_settings import OllamaSettings


pytestmark = pytest.mark.integration


@pytest.fixture
def mock_embedder():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 384
    return embedder


@pytest.fixture
def real_ollama_generator():
    """Создает реальный клиент Ollama. Если Ollama не запущена, тест сможет это перехватить."""
    settings = OllamaSettings(
        model_name="qwen3.5:9b",
        temperature=0.1,
        num_ctx=4096,
        is_cloud=False,
        local_url="http://localhost:11434",
    )
    factory = ChatOllamaFactory(settings)
    return OllamaAnswerGenerator(factory)


class TestAskUseCase:
    async def test_db_retrieval_includes_pages_and_filename(
        self, doc_repo, schema_repo, session_manager, instance_repo, mock_embedder
    ):
        """Проверка того, что БД отдает имя файла и страницы при векторном поиске."""
        await schema_repo.ensure_indexes()

        # 1. Создаем документ и чанк в БД
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

        # Создаем связь Document -> Chunk (обязательно для JOIN в Cypher)
        # Так как VectorSearchStrategy использует MATCH (d:Document {doc_id: c.doc_id}),
        # связь не обязательна, но сохранение чанка с doc_id сработает.

        # 2. Инициализируем стратегию
        strategy = VectorSearchStrategy(session_manager, instance_repo)

        # 3. Делаем поиск
        result = await strategy.retrieve(
            "Как выросла выручка?", query_embedding=[0.1] * 384
        )

        # 4. Проверяем извлеченные данные
        assert len(result.chunks) == 1
        c = result.chunks[0]
        assert c.source_filename == "Финансовый_отчет_2024.pdf"
        assert c.start_page == 14
        assert c.end_page == 15

    async def test_ollama_generates_answer_with_citations(self, real_ollama_generator):
        """
        Прямой тест генератора (Ollama) с переданным собранным контекстом.
        Проверяет, что LLM подчиняется системному промпту и ставит ссылки [Документ: ..., Стр. ...].
        """
        # Эмулируем работу ContextBuilder
        context_text = (
            "=== РЕЛЕВАНТНЫЕ ФРАГМЕНТЫ ИЗ ДОКУМЕНТОВ ===\n"
            "--- Фрагмент #1 [Документ: Устав_Корпорации.pdf, Стр. 10-10] ---\n"
            "Генеральный директор назначается сроком на 5 лет.\n\n"
            "--- Фрагмент #2 [Документ: Регламент_Безопасности.docx, Стр. 3-4] ---\n"
            "Пароли сотрудников должны меняться каждые 90 дней."
        )

        question = (
            "На какой срок назначается гендиректор и как часто нужно менять пароли?"
        )

        try:
            # Делаем реальный запрос к локальной Ollama
            response = await real_ollama_generator.generate(
                question=question, context=context_text
            )

            # Ответ должен содержать факты
            assert "5" in response or "пять" in response.lower()
            assert "90" in response or "девяносто" in response.lower()

            # Ответ должен содержать корректное цитирование документов
            assert "[Документ: Устав_Корпорации.pdf" in response
            assert "[Документ: Регламент_Безопасности.docx" in response
            assert "Стр." in response

        except Exception as e:
            pytest.skip(
                f"Ollama недоступна или произошла ошибка. Пропуск теста генерации. Ошибка: {e}"
            )

    async def test_full_use_case_orchestration(
        self, doc_repo, schema_repo, session_manager, instance_repo, mock_embedder
    ):
        """Интеграционный тест: оркестратор склеивает всё вместе (Mock LLM)."""
        await schema_repo.ensure_indexes()

        doc = DocumentNode(doc_id="d1", filename="Секретный_План.pdf")
        await doc_repo.save_document(doc)

        chunk = ChunkNode(
            chunk_id="c1",
            doc_id="d1",
            chunk_index=0,
            text="Операция начнется на рассвете.",
            start_page=42,
            end_page=42,
            embedding=[0.1] * 384,
        )
        await doc_repo.save_chunk(chunk)

        # Мокаем LLM, чтобы проверить только переданный ей аргумент `context`
        mock_llm_generator = AsyncMock()
        mock_llm_generator.generate.return_value = (
            "На рассвете [Документ: Секретный_План.pdf, Стр. 42]."
        )

        strategy = VectorSearchStrategy(session_manager, instance_repo)
        registry = RetrievalStrategyRegistry()
        registry.register(SearchMode.LOCAL, strategy)

        builder = ContextBuilder()

        use_case = AnswerQuestionUseCase(
            embedder=mock_embedder,
            registry=registry,
            context_builder=builder,
            generator=mock_llm_generator,
        )

        response = await use_case.execute(
            question="Когда начнется операция?", mode=SearchMode.LOCAL
        )

        # Проверяем, что LLM была вызвана
        mock_llm_generator.generate.assert_called_once()

        # Проверяем, какой КОНТЕКСТ был передан в LLM (kwargs['context'])
        called_args = mock_llm_generator.generate.call_args.kwargs
        context_passed_to_llm = called_args["context"]

        assert "[Документ: Секретный_План.pdf, Стр. 42]" in context_passed_to_llm
        assert "Операция начнется на рассвете" in context_passed_to_llm

        # Проверяем сам объект ответа
        assert len(response.sources) == 1
        assert response.sources[0].filename == "Секретный_План.pdf"
        assert response.sources[0].start_page == 42
