from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from src.config.app_settings import AppSettings
from src.config.extraction_settings import ExtractionSettings
from src.config.llm_settings import LLMSettings
from src.config.neo4j_settings import Neo4jSettings
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.services.synonym_resolver import ISynonymResolver
from src.infrastructure.docling.doc_processor import DocProcessor
from src.infrastructure.embeddings.sentence_transformer_embedding_service import (
    SentenceTransformerService,
)
from src.infrastructure.llm.clients.llm_entity_extractor import OllamaClient
from src.infrastructure.llm.clients.llm_synonym_resolver import (
    OllamaSynonymResolver,
)
from src.infrastructure.llm.llm_factory import ChatModelFactory
from src.persistence.neo4j.neo4j_document_repository import Neo4jDocumentRepository
from src.persistence.neo4j.neo4j_edge_repository import Neo4jEdgeRepository
from src.persistence.neo4j.neo4j_instance_repository import Neo4jInstanceRepository
from src.persistence.neo4j.neo4j_schema_repository import Neo4jSchemaRepository
from src.persistence.neo4j.session_manager import Neo4jSessionManager


class InfrastructureProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_session_manager(
        self,
        settings: Neo4jSettings,
    ) -> AsyncIterator[Neo4jSessionManager]:
        sm = Neo4jSessionManager(settings)
        yield sm
        await sm.close()

    @provide(scope=Scope.APP)
    def provide_schema_repo(
        self,
        sm: Neo4jSessionManager,
    ) -> ISchemaRepository:
        return Neo4jSchemaRepository(sm)

    @provide(scope=Scope.APP)
    def provide_document_repo(
        self,
        sm: Neo4jSessionManager,
    ) -> IDocumentRepository:
        return Neo4jDocumentRepository(sm)

    @provide(scope=Scope.APP)
    def provide_instance_repo(
        self,
        sm: Neo4jSessionManager,
    ) -> IInstanceRepository:
        return Neo4jInstanceRepository(sm)

    @provide(scope=Scope.APP)
    def provide_edge_repo(
        self,
        sm: Neo4jSessionManager,
    ) -> IEdgeRepository:
        return Neo4jEdgeRepository(sm)

    @provide(scope=Scope.APP)
    def provide_llm_factory(self, settings: LLMSettings) -> ChatModelFactory:
        return ChatModelFactory(settings)

    @provide(scope=Scope.APP)
    def provide_llm(
        self,
        factory: ChatModelFactory,
        extraction_settings: ExtractionSettings,
    ) -> ILLMClient:
        return OllamaClient(factory, extraction_settings)

    @provide(scope=Scope.APP)
    def provide_synonym_resolver(
        self,
        factory: ChatModelFactory,
    ) -> ISynonymResolver:
        return OllamaSynonymResolver(factory)

    @provide(scope=Scope.APP)
    def provide_embedder(self, config: AppSettings) -> IEmbeddingService:
        return SentenceTransformerService(config.embedding_model)

    @provide(scope=Scope.APP)
    def provide_parser(self, config: AppSettings) -> DocProcessor:
        return DocProcessor(config.chunking, config.parsing)
