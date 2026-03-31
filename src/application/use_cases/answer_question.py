import logging
from src.domain.models.search import SearchMode
from src.domain.models.qa import AnswerResponse, SourceReference
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
        self, question: str, mode: SearchMode = SearchMode.HYBRID, top_k: int = 10
    ) -> AnswerResponse:
        logger.info(
            f"❓ Question: «{question[:80]}…» | mode={mode.value} | top_k={top_k}"
        )
        query_embedding = await self.embedder.embed_text(question)
        strategy = self.registry.get(mode)

        retrieval_result = await strategy.retrieve(
            query=question, query_embedding=query_embedding, top_k=top_k
        )
        context_text = self.context_builder.build(retrieval_result)
        answer_text = await self.generator.generate(
            question=question, context=context_text
        )

        sources = [
            SourceReference(
                chunk_id=c.chunk_id,
                filename=c.source_filename,
                chunk_index=c.chunk_index,
                relevance=c.score,
                start_page=c.start_page,
                end_page=c.end_page,
            )
            for c in sorted(
                retrieval_result.chunks, key=lambda c: c.score, reverse=True
            )
        ]

        return AnswerResponse(
            answer=answer_text,
            sources=sources,
            search_mode=mode.value,
            context_stats=self.context_builder.get_stats(retrieval_result),
        )
