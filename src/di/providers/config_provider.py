from dishka import Provider, Scope, provide
from src.config.base import AppConfig

class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def get_config(self) -> AppConfig:
        return AppConfig()