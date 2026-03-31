import logging
from typing import Any, List, TypeVar
from src.persistence.neo4j.session_manager import Neo4jSessionManager
from .queries.base import Neo4jQuery

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Neo4jBaseRepository:
    def __init__(self, session_manager: Neo4jSessionManager):
        self._sm = session_manager

    @property
    def _settings(self):
        return self._sm.settings

    def _log_query_execution(self, query_obj: Neo4jQuery[Any]) -> None:
        params = query_obj.get_params()
        logger.debug(f"Executing {query_obj} | params keys: {list(params.keys())}")

    async def _execute(self, query: Neo4jQuery[Any]) -> None:
        """Выполняет запрос на запись (без возврата данных)."""
        self._log_query_execution(query)
        async with self._sm.session() as s:
            result = await s.run(query.get_query(), query.get_params())
            await result.consume()

    async def _fetch_all(self, query: Neo4jQuery[T]) -> List[T]:
        """Выполняет запрос на чтение и автоматически маппит результаты в тип T."""
        self._log_query_execution(query)
        async with self._sm.session() as s:
            result = await s.run(query.get_query(), query.get_params())
            data = await result.data()
            return [query.map_record(record) for record in data]
