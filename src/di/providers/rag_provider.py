from dishka import Provider, Scope, provide
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.persistence.neo4j.session_manager import Neo4jSessionManager
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.infrastructure.llm.clients.llm_answer_generator import OllamaAnswerGenerator
from src.infrastructure.retrieval.vector_search_strategy import VectorSearchStrategy
from src.infrastructure.retrieval.ppr_strategy import PPRStrategy
from src.infrastructure.retrieval.community_strategy import CommunityStrategy
from src.infrastructure.retrieval.hybrid_strategy import HybridStrategy
from src.infrastructure.neo4j_gds.gds_analytics_service import Neo4jGDSAnalyticsService
from src.application.services.retrieval_registry import RetrievalStrategyRegistry
from src.application.services.context_builder import ContextBuilder
from src.application.use_cases.answer_question import AnswerQuestionUseCase
from src.application.use_cases.build_communities import BuildCommunitiesUseCase

# Исправление F821 и missing args
from src.domain.models.search import SearchMode
from src.config.rag_settings import RAGSettings


class RAGProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_analytics(self, sm: Neo4jSessionManager) -> IGraphAnalyticsService:
        return Neo4jGDSAnalyticsService(sm)

    @provide(scope=Scope.APP)
    def provide_generator(self, factory: ChatOllamaFactory) -> IAnswerGenerator:
        return OllamaAnswerGenerator(factory)

    @provide(scope=Scope.APP)
    def provide_vector_strategy(
        self, sm: Neo4jSessionManager, instance_repo: IInstanceRepository
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
        registry.register(SearchMode.HYBRID, HybridStrategy([vector, community]))
        return registry

    @provide(scope=Scope.APP)
    def provide_context_builder(self, rag_settings: RAGSettings) -> ContextBuilder:
        return ContextBuilder(settings=rag_settings)

    answer_question = provide(AnswerQuestionUseCase, scope=Scope.APP)
    build_communities = provide(BuildCommunitiesUseCase, scope=Scope.APP)
