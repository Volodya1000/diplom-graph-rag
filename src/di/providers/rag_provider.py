"""DI-провайдер для RAG: стратегии, реестр, use case."""

from dishka import Provider, Scope, provide

from src.config.ollama_settings import OllamaSettings
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.services.graph_analytics_service import IGraphAnalyticsService
from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.value_objects.search_context import SearchMode

from src.persistence.neo4j.session_manager import Neo4jSessionManager

from src.infrastructure.retrieval.vector_search_strategy import VectorSearchStrategy
from src.infrastructure.retrieval.ppr_strategy import PPRStrategy
from src.infrastructure.retrieval.community_strategy import CommunityStrategy
from src.infrastructure.retrieval.hybrid_strategy import HybridStrategy
from src.infrastructure.neo4j_gds.gds_analytics_service import Neo4jGDSAnalyticsService
from src.infrastructure.llm.clients.ollama_answer_generator import OllamaAnswerGenerator

from src.application.services.retrieval_registry import RetrievalStrategyRegistry
from src.application.services.context_builder import ContextBuilder
from src.application.use_cases.answer_question import AnswerQuestionUseCase


class RAGProvider(Provider):

    # --- Analytics ---

    @provide(scope=Scope.APP)
    def provide_analytics(
        self, sm: Neo4jSessionManager,
    ) -> IGraphAnalyticsService:
        return Neo4jGDSAnalyticsService(sm)

    # --- Answer Generator ---

    @provide(scope=Scope.APP)
    def provide_generator(
        self, settings: OllamaSettings,
    ) -> IAnswerGenerator:
        return OllamaAnswerGenerator(settings)

    # --- Strategies ---

    @provide(scope=Scope.APP)
    def provide_vector_strategy(
        self,
        sm: Neo4jSessionManager,
        instance_repo: IInstanceRepository,
    ) -> VectorSearchStrategy:
        return VectorSearchStrategy(sm, instance_repo)

    @provide(scope=Scope.APP)
    def provide_ppr_strategy(
        self,
        sm: Neo4jSessionManager,
        instance_repo: IInstanceRepository,
        analytics: IGraphAnalyticsService,
    ) -> PPRStrategy:
        return PPRStrategy(sm, instance_repo, analytics)

    @provide(scope=Scope.APP)
    def provide_community_strategy(
        self,
        analytics: IGraphAnalyticsService,
        embedder: IEmbeddingService,
        sm: Neo4jSessionManager,
    ) -> CommunityStrategy:
        return CommunityStrategy(analytics, embedder, sm)

    # --- Registry ---

    @provide(scope=Scope.APP)
    def provide_registry(
        self,
        vector: VectorSearchStrategy,
        ppr: PPRStrategy,
        community: CommunityStrategy,
    ) -> RetrievalStrategyRegistry:
        registry = RetrievalStrategyRegistry()

        registry.register(SearchMode.LOCAL, vector)
        registry.register(SearchMode.LOCAL_PPR, ppr)
        registry.register(SearchMode.GLOBAL, community)
        registry.register(
            SearchMode.HYBRID,
            HybridStrategy([vector, community]),
        )
        return registry

    # --- Context Builder ---

    @provide(scope=Scope.APP)
    def provide_context_builder(self) -> ContextBuilder:
        return ContextBuilder()

    # --- Use Case ---

    answer_question = provide(AnswerQuestionUseCase, scope=Scope.APP)