from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from src.config.extraction_settings import ExtractionSettings
from src.config.neo4j_settings import Neo4jSettings
from src.config.ollama_settings import OllamaSettings
from src.config.base import AppConfig
from src.config.chunking_settings import ChunkingSettings
from src.config.parsing_settings import ParsingSettings

from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.domain.interfaces.services.synonym_resolver import ISynonymResolver

from src.persistence.neo4j.session_manager import Neo4jSessionManager
from src.persistence.neo4j.neo4j_schema_repository import Neo4jSchemaRepository
from src.persistence.neo4j.neo4j_document_repository import Neo4jDocumentRepository
from src.persistence.neo4j.neo4j_instance_repository import Neo4jInstanceRepository
from src.persistence.neo4j.neo4j_edge_repository import Neo4jEdgeRepository

from src.infrastructure.embeddings.sentence_transformer_embedding_service import (
    SentenceTransformerService,
)
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.infrastructure.llm.clients.ollama_client import OllamaClient
from src.infrastructure.llm.clients.ollama_synonym_resolver import (
    OllamaSynonymResolver,
)
from src.infrastructure.docling.doc_processor import DocProcessor


class InfrastructureProvider(Provider):

    # --- Neo4j: один драйвер → четыре репозитория ---

    @provide(scope=Scope.APP)
    async def provide_session_manager(
        self, settings: Neo4jSettings,
    ) -> AsyncIterator[Neo4jSessionManager]:
        sm = Neo4jSessionManager(settings)
        yield sm
        await sm.close()

    @provide(scope=Scope.APP)
    def provide_schema_repo(
        self, sm: Neo4jSessionManager,
    ) -> ISchemaRepository:
        return Neo4jSchemaRepository(sm)

    @provide(scope=Scope.APP)
    def provide_document_repo(
        self, sm: Neo4jSessionManager,
    ) -> IDocumentRepository:
        return Neo4jDocumentRepository(sm)

    @provide(scope=Scope.APP)
    def provide_instance_repo(
        self, sm: Neo4jSessionManager,
    ) -> IInstanceRepository:
        return Neo4jInstanceRepository(sm)

    @provide(scope=Scope.APP)
    def provide_edge_repo(
        self, sm: Neo4jSessionManager,
    ) -> IEdgeRepository:
        return Neo4jEdgeRepository(sm)

    # --- LLM: одна фабрика → три клиента ---

    @provide(scope=Scope.APP)
    def provide_llm_factory(
        self, settings: OllamaSettings,
    ) -> ChatOllamaFactory:
        return ChatOllamaFactory(settings)

    @provide(scope=Scope.APP)
    def provide_llm(
            self,
            factory: ChatOllamaFactory,
            extraction_settings: ExtractionSettings,
    ) -> ILLMClient:
        return OllamaClient(factory, extraction_settings)

    @provide(scope=Scope.APP)
    def provide_synonym_resolver(
        self, factory: ChatOllamaFactory,
    ) -> ISynonymResolver:
        return OllamaSynonymResolver(factory)

    # --- Embeddings ---

    @provide(scope=Scope.APP)
    def provide_embedder(self, config: AppConfig) -> IEmbeddingService:
        return SentenceTransformerService(config.EMBEDDING_MODEL)

    # --- Document processing ---

    @provide(scope=Scope.APP)
    def provide_parser(self) -> DocProcessor:
        return DocProcessor(ChunkingSettings(), ParsingSettings())