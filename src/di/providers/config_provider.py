from dishka import Provider, Scope, provide

from src.config.neo4j_settings import Neo4jSettings
from src.config.ollama_settings import OllamaSettings
from src.config.base import AppConfig

class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def get_config(self) -> AppConfig:
        return AppConfig()

    @provide(scope=Scope.APP)
    def provide_neo4j_settings(self) -> Neo4jSettings:
        return Neo4jSettings()

    @provide(scope=Scope.APP)
    def provide_ollama_settings(self) -> OllamaSettings:
        return OllamaSettings()
