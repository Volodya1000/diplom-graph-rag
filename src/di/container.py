# src/di/setup_di.py
from dishka import make_async_container

from src.di.providers.application_provider import ApplicationProvider
from src.di.providers.config_provider import ConfigProvider
from src.di.providers.infrastructure_provider import InfrastructureProvider
from src.di.providers.rag_provider import RAGProvider


def setup_di(
    config_path: str = "config.yml",
    override_path: str | None = None,
):
    return make_async_container(
        ConfigProvider(
            config_path=config_path,
            override_path=override_path,
        ),
        InfrastructureProvider(),
        ApplicationProvider(),
        RAGProvider(),
    )
