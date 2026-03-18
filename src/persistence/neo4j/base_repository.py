"""
Базовый класс для Neo4j-репозиториев.
Убирает дублирование session-boilerplate.
"""

from typing import Any, Dict, List, Optional

from src.persistence.neo4j.session_manager import Neo4jSessionManager


class Neo4jBaseRepository:
    def __init__(self, session_manager: Neo4jSessionManager):
        self._sm = session_manager

    @property
    def _settings(self):
        return self._sm.settings

    async def _execute(
            self, query: str, params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Выполнить запрос без возврата данных."""
        async with self._sm.session() as s:
            result = await s.run(query, params or {})
            await result.consume()

    async def _fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Выполнить запрос и вернуть все записи."""
        async with self._sm.session() as s:
            result = await s.run(query, params or {})
            return await result.data()