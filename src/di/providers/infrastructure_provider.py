from dishka import Provider, Scope, provide
from src.config.base import AppConfig
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.llm.llm_client import ILLMClient

from src.persistence.neo4j.neo4j_repository import Neo4jRepository
from src.infrastructure.embeddings.sentence_transformer_embedding_service import SentenceTransformerService
from src.infrastructure.llm.clients.ollama_client import OllamaClient
from src.infrastructure.docling.doc_processor import DocProcessor
from src.config.chunking_settings import ChunkingSettings
from src.config.parsing_settings import ParsingSettings


class InfrastructureProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_neo4j(self, config: AppConfig) -> IGraphRepository:
        return Neo4jRepository(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD)

    @provide(scope=Scope.APP)
    def provide_embedder(self, config: AppConfig) -> IEmbeddingService:
        return SentenceTransformerService(config.EMBEDDING_MODEL)

    @provide(scope=Scope.APP)
    def provide_llm(self, config: AppConfig) -> ILLMClient:
        return OllamaClient(config.OLLAMA_BASE_URL, config.OLLAMA_MODEL)

    @provide(scope=Scope.APP)
    def provide_parser(self) -> DocProcessor:
        return DocProcessor(ChunkingSettings(), ParsingSettings())