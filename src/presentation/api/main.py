"""Точка входа для FastAPI."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka
from src.di.container import setup_di
from src.presentation.api.routers import chat, documents
from src.utils.logging import setup_logging
import logging

setup_logging(level=logging.INFO, disable_verbose=True)
logger = logging.getLogger(__name__)

# Создаём контейнер один раз
container = setup_di()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan-события: запуск и остановка приложения."""
    # ==================== STARTUP ====================
    try:
        from src.domain.interfaces.repositories.schema_repository import (
            ISchemaRepository,
        )

        schema_repo = await container.get(ISchemaRepository)
        await schema_repo.ensure_indexes()
        logger.info("📐 Векторные индексы Neo4j успешно обеспечены (startup)")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании индексов на старте: {e}")

    yield

    # ==================== SHUTDOWN ====================
    await container.close()
    logger.info("🔌 DI-контейнер и Neo4j driver закрыты")


app = FastAPI(
    title="GraphRAG API",
    description="Knowledge Graph RAG with Neo4j and Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)

setup_dishka(container, app)


@app.get("/health")
def health_check():
    return {"status": "ok"}
