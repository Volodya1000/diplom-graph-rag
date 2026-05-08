# tests/integration/conftest.py
from __future__ import annotations

# Самое начало файла — до любых импортов, чтобы заглушить шум testcontainers
import warnings
from collections.abc import AsyncGenerator, Callable, Generator

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"testcontainers\.neo4j",
    append=False,
)
warnings.filterwarnings(
    "ignore",
    message="The wait_for_logs function with string or callable predicates is deprecated",
    category=DeprecationWarning,
    append=False,
)
warnings.filterwarnings(
    "ignore",
    message="The @wait_container_is_ready decorator is deprecated",
    category=DeprecationWarning,
    append=False,
)

import pytest
import pytest_asyncio
from testcontainers.neo4j import Neo4jContainer

from src.config.app_settings import AppSettings, load_config  # поправь путь, если файл у тебя называется иначе
from src.config.llm_settings import LLMSettings
from src.config.neo4j_settings import Neo4jSettings
from src.config.rag_settings import RAGSettings
from src.persistence.neo4j.neo4j_document_repository import Neo4jDocumentRepository
from src.persistence.neo4j.neo4j_edge_repository import Neo4jEdgeRepository
from src.persistence.neo4j.neo4j_instance_repository import Neo4jInstanceRepository
from src.persistence.neo4j.neo4j_schema_repository import Neo4jSchemaRepository
from src.persistence.neo4j.session_manager import Neo4jSessionManager


@pytest.fixture(scope="session")
def app_settings() -> AppSettings:
    """
    Единый источник правды для integration-тестов.
    Конфиг грузится один раз из YAML и .env.
    """
    return load_config()


@pytest.fixture(scope="session")
def neo4j_container() -> Generator[Neo4jContainer, None, None]:
    """Запускает Neo4j в Docker один раз для всех integration-тестов."""
    container = Neo4jContainer(image="neo4j:5.26-community")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def neo4j_settings(
    app_settings: AppSettings,
    neo4j_container: Neo4jContainer,
) -> Neo4jSettings:
    host = neo4j_container.get_container_host_ip()
    port = neo4j_container.get_exposed_port(7687)
    bolt_url = f"bolt://{host}:{port}"

    return Neo4jSettings(
        uri=bolt_url,
        user=app_settings.neo4j.user,
        password=app_settings.neo4j.password,
        embedding_dim=app_settings.neo4j.embedding_dim,
        vector_search_threshold=app_settings.neo4j.vector_search_threshold,
    )


@pytest_asyncio.fixture
async def session_manager(neo4j_settings: Neo4jSettings) -> AsyncGenerator[Neo4jSessionManager, None]:
    sm = Neo4jSessionManager(neo4j_settings)
    yield sm
    await sm.close()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(session_manager: Neo4jSessionManager):
    """Очищает все ноды и рёбра перед каждым тестом."""
    async with session_manager.session() as s:
        result = await s.run("MATCH (n) DETACH DELETE n")
        await result.consume()


@pytest.fixture
def schema_repo(session_manager: Neo4jSessionManager) -> Neo4jSchemaRepository:
    return Neo4jSchemaRepository(session_manager)


@pytest.fixture
def doc_repo(session_manager: Neo4jSessionManager) -> Neo4jDocumentRepository:
    return Neo4jDocumentRepository(session_manager)


@pytest.fixture
def instance_repo(session_manager: Neo4jSessionManager) -> Neo4jInstanceRepository:
    return Neo4jInstanceRepository(session_manager)


@pytest.fixture
def edge_repo(session_manager: Neo4jSessionManager) -> Neo4jEdgeRepository:
    return Neo4jEdgeRepository(session_manager)


@pytest.fixture(scope="session")
def llm_settings(app_settings: AppSettings) -> LLMSettings:
    return app_settings.llm


@pytest.fixture(scope="session")
def rag_settings(app_settings: AppSettings) -> RAGSettings:
    return app_settings.rag


@pytest.fixture(scope="session")
def embedding_dim(app_settings: AppSettings) -> int:
    return app_settings.neo4j.embedding_dim


@pytest.fixture
def embedding_factory(embedding_dim: int) -> Callable[[], list[float]]:
    def _factory() -> list[float]:
        return [0.1] * embedding_dim

    return _factory


@pytest.fixture
def mock_embedder(embedding_factory: Callable[[], list[float]]):
    from unittest.mock import AsyncMock

    embedder = AsyncMock()
    embedder.embed_text.return_value = embedding_factory()
    return embedder


@pytest.fixture
def mock_file_storage():
    from unittest.mock import MagicMock

    storage = MagicMock()
    storage.get_download_url.side_effect = lambda filename: f"http://test-api/uploads/{filename}"
    return storage
