# src/di/providers/config_provider.py
from __future__ import annotations

from dishka import Provider, Scope, provide

from src.config.app_settings import AppSettings, load_config
from src.config.chunking_settings import ChunkingSettings
from src.config.extraction_settings import ExtractionSettings
from src.config.llm_settings import LLMSettings
from src.config.neo4j_settings import Neo4jSettings
from src.config.parsing_settings import ParsingSettings
from src.config.rag_settings import RAGSettings


class ConfigProvider(Provider):
    def __init__(
        self,
        config_path: str = "config.yml",
        override_path: str | None = None,
    ) -> None:
        super().__init__()
        self._config_path = config_path
        self._override_path = override_path

    @provide(scope=Scope.APP)
    def provide_app_settings(self) -> AppSettings:
        return load_config(
            yaml_path=self._config_path,
            override_path=self._override_path,
        )

    @provide(scope=Scope.APP)
    def provide_neo4j_settings(self, app_config: AppSettings) -> Neo4jSettings:
        return app_config.neo4j

    @provide(scope=Scope.APP)
    def provide_llm_settings(self, app_config: AppSettings) -> LLMSettings:
        return app_config.llm

    @provide(scope=Scope.APP)
    def provide_extraction_settings(
        self,
        app_config: AppSettings,
    ) -> ExtractionSettings:
        return app_config.extraction

    @provide(scope=Scope.APP)
    def provide_chunking_settings(self, app_config: AppSettings) -> ChunkingSettings:
        return app_config.chunking

    @provide(scope=Scope.APP)
    def provide_parsing_settings(self, app_config: AppSettings) -> ParsingSettings:
        return app_config.parsing

    @provide(scope=Scope.APP)
    def provide_rag_settings(self, app_config: AppSettings) -> RAGSettings:
        return app_config.rag
