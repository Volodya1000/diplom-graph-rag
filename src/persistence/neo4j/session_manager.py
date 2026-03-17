"""
Управление жизненным циклом Neo4j-драйвера.
"""

import logging
from neo4j import AsyncGraphDatabase, AsyncDriver, NotificationDisabledCategory

from src.config.neo4j_settings import Neo4jSettings

logger = logging.getLogger(__name__)


class Neo4jSessionManager:
    def __init__(self, settings: Neo4jSettings):
        self.settings = settings
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(
            settings.uri,
            auth=(settings.user, settings.password_value),
            notifications_disabled_categories=[
                NotificationDisabledCategory.UNRECOGNIZED,
                NotificationDisabledCategory.HINT,
                NotificationDisabledCategory.GENERIC,
            ],
        )
        logger.info(f"🔌 Neo4j driver created → {settings.uri}")

    def session(self, **kwargs):
        return self._driver.session(**kwargs)

    async def close(self) -> None:
        await self._driver.close()
        logger.info("🔌 Neo4j driver closed")