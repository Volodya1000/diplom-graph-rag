from dishka import make_async_container
from src.di.providers.config_provider import ConfigProvider
from src.di.providers.infrastructure_provider import InfrastructureProvider
from src.di.providers.application_provider import ApplicationProvider

def setup_di():
    return make_async_container(
        ConfigProvider(),
        InfrastructureProvider(),
        ApplicationProvider(),
    )