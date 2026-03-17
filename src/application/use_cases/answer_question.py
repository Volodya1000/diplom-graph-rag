"""
Use Case: Ответ на вопрос пользователя по графу знаний.

Оркестрирует:
  1. Эмбеддинг вопроса
  2. Выбор стратегии по SearchMode
  3. Извлечение контекста (strategy.retrieve)
  4. Сборка контекста (ContextBuilder)
  5. Генерация ответа (IAnswerGenerator)
"""

import logging

from src.domain.value_objects.search_context import SearchMode, RetrievalResult
from src.domain.value_objects.answer_response import AnswerResponse, SourceReference
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.application.services.retrieval_registry import RetrievalStrategyRegistry
from src.application.services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class AnswerQuestionUseCase:
    def __init__(
        self,
        embedder: IEmbeddingService,
        registry: RetrievalStrategyRegistry,
        context_builder: ContextBuilder,
        generator: IAnswerGenerator,
    ):
        self.embedder = embedder
        self.registry = registry
        self.context_builder = context_builder
        self.generator = generator

    async def execute(
        self,
        question: str,
        mode: SearchMode = SearchMode.HYBRID,
        top_k: int = 10,
    ) -> AnswerResponse:
        logger.info(
            f"❓ Question: «{question[:80]}…» | "
            f"mode={mode.value} | top_k={top_k}"
        )

        # 1. Эмбеддинг вопроса
        query_embedding = await self.embedder.embed_text(question)

        # 2. Выбор стратегии
        strategy = self.registry.get(mode)
        logger.info(f"🔍 Стратегия: {strategy.name}")

        # 3. Извлечение контекста
        retrieval_result: RetrievalResult = await strategy.retrieve(
            query=question,
            query_embedding=query_embedding,
            top_k=top_k,
        )
        logger.info(
            f"📦 Контекст: {len(retrieval_result.chunks)} чанков, "
            f"{len(retrieval_result.triples)} троек, "
            f"{len(retrieval_result.communities)} сообществ"
        )

        # 4. Сборка контекста
        context_text = self.context_builder.build(retrieval_result)

        # 5. Генерация ответа
        answer_text = await self.generator.generate(
            question=question,
            context=context_text,
        )

        # 6. Формирование ответа
        sources = [
            SourceReference(
                chunk_id=c.chunk_id,
                filename=c.source_filename,
                chunk_index=c.chunk_index,
                relevance=c.score,
            )
            for c in sorted(
                retrieval_result.chunks,
                key=lambda c: c.score,
                reverse=True,
            )[:5]
        ]

        return AnswerResponse(
            answer=answer_text,
            sources=sources,
            search_mode=mode.value,
            context_stats=self.context_builder.get_stats(retrieval_result),
        )