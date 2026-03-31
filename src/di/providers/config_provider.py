from dishka import Provider, Scope, provide

from src.config.app_settings import AppSettings, load_config
from src.config.neo4j_settings import Neo4jSettings
from src.config.ollama_settings import OllamaSettings
from src.config.extraction_settings import ExtractionSettings
from src.config.chunking_settings import ChunkingSettings
from src.config.parsing_settings import ParsingSettings


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_app_settings(self) -> AppSettings:
        # Фабрика загружает конфиг при старте приложения
        return load_config("config.yml")

    @provide(scope=Scope.APP)
    def provide_neo4j_settings(self, app_config: AppSettings) -> Neo4jSettings:
        return app_config.neo4j

    @provide(scope=Scope.APP)
    def provide_ollama_settings(self, app_config: AppSettings) -> OllamaSettings:
        return app_config.ollama

    @provide(scope=Scope.APP)
    def provide_extraction_settings(
        self, app_config: AppSettings
    ) -> ExtractionSettings:
        return app_config.extraction

    @provide(scope=Scope.APP)
    def provide_chunking_settings(self, app_config: AppSettings) -> ChunkingSettings:
        return app_config.chunking

    @provide(scope=Scope.APP)
    def provide_parsing_settings(self, app_config: AppSettings) -> ParsingSettings:
        return app_config.parsing
