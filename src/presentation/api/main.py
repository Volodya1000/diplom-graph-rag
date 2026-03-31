"""Точка входа для FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import setup_dishka

from src.di.container import setup_di
from src.presentation.api.routers import chat, documents
from src.utils.logging import setup_logging
import logging

setup_logging(level=logging.INFO, disable_verbose=True)

app = FastAPI(
    title="GraphRAG API",
    description="Knowledge Graph RAG with Neo4j and Ollama",
    version="1.0.0",
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

container = setup_di()
setup_dishka(container, app)


@app.get("/health")
def health_check():
    return {"status": "ok"}
