# Самое начало файла — ДО ЛЮБЫХ ИМПОРТОВ
import warnings

# Фильтр 1: глушим все DeprecationWarning из модуля testcontainers.neo4j
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"testcontainers\.neo4j",
    append=False
)

# Фильтр 2: точное сообщение про wait_for_logs (самое актуальное сейчас)
warnings.filterwarnings(
    "ignore",
    message="The wait_for_logs function with string or callable predicates is deprecated",
    category=DeprecationWarning,
    append=False
)

# Фильтр 3: точное сообщение про декоратор (на случай, если оно ещё где-то всплывёт)
warnings.filterwarnings(
    "ignore",
    message="The @wait_container_is_ready decorator is deprecated",
    category=DeprecationWarning,
    append=False
)

# Теперь уже безопасно импортировать всё остальное
import pytest
import pytest_asyncio
from testcontainers.neo4j import Neo4jContainer
from pydantic import SecretStr

from src.config.neo4j_settings import Neo4jSettings
from src.persistence.neo4j.session_manager import Neo4jSessionManager
from src.persistence.neo4j.neo4j_schema_repository import Neo4jSchemaRepository
from src.persistence.neo4j.neo4j_document_repository import Neo4jDocumentRepository
from src.persistence.neo4j.neo4j_instance_repository import Neo4jInstanceRepository
from src.persistence.neo4j.neo4j_edge_repository import Neo4jEdgeRepository


# ─── контейнер (один на сессию) ───
@pytest.fixture(scope="session")
def neo4j_container():
    """Запускает Neo4j в Docker один раз для всех integration-тестов."""
    container = Neo4jContainer(image="neo4j:5.26-community")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def neo4j_settings(neo4j_container) -> Neo4jSettings:
    host = neo4j_container.get_container_host_ip()
    port = neo4j_container.get_exposed_port(7687)
    bolt_url = f"bolt://{host}:{port}"
    return Neo4jSettings(
        uri=bolt_url,
        user="neo4j",
        password=SecretStr("password"),
        embedding_dim=384,
        vector_search_threshold=0.70,
    )


# ─── SessionManager (ОДИН НА ТЕСТ) ───
@pytest_asyncio.fixture
async def session_manager(neo4j_settings) -> Neo4jSessionManager:
    sm = Neo4jSessionManager(neo4j_settings)
    yield sm
    await sm.close()


# ─── Очистка перед каждым тестом ───
@pytest_asyncio.fixture(autouse=True)
async def clean_db(session_manager):
    """Очищает ВСЕ ноды и рёбра перед каждым тестом."""
    async with session_manager.session() as s:
        result = await s.run("MATCH (n) DETACH DELETE n")
        await result.consume()  # обязательно!


# ─── Репозитории ───
@pytest.fixture
def schema_repo(session_manager) -> Neo4jSchemaRepository:
    return Neo4jSchemaRepository(session_manager)


@pytest.fixture
def doc_repo(session_manager) -> Neo4jDocumentRepository:
    return Neo4jDocumentRepository(session_manager)


@pytest.fixture
def instance_repo(session_manager) -> Neo4jInstanceRepository:
    return Neo4jInstanceRepository(session_manager)


@pytest.fixture
def edge_repo(session_manager) -> Neo4jEdgeRepository:
    return Neo4jEdgeRepository(session_manager)