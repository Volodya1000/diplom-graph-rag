"""
Управление жизненным циклом Neo4j-драйвера.
"""

import logging
from neo4j import AsyncGraphDatabase, AsyncDriver

from src.config.neo4j_settings import Neo4jSettings

logger = logging.getLogger(__name__)


class Neo4jSessionManager:
    def __init__(self, settings: Neo4jSettings):
        self.settings = settings

        auth = None
        if settings.password_value:
            auth = (settings.user, settings.password_value)

        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            settings.uri,
            auth=auth,
            notifications_min_severity="OFF",
        )
        logger.info(f"🔌 Neo4j driver created → {settings.uri}")

    def session(self, **kwargs):
        return self._driver.session(**kwargs)

    async def close(self) -> None:
        await self._driver.close()
        logger.info("🔌 Neo4j driver closed")