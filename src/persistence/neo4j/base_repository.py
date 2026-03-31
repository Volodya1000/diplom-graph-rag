import logging
from typing import Any, Dict, List, Optional, Union
from src.persistence.neo4j.session_manager import Neo4jSessionManager
from .queries.base import Neo4jQuery

logger = logging.getLogger(__name__)


class Neo4jBaseRepository:
    def __init__(self, session_manager: Neo4jSessionManager):
        self._sm = session_manager

    @property
    def _settings(self):
        return self._sm.settings

    def _log_query_execution(self, query_obj: Neo4jQuery) -> None:
        params = query_obj.get_params()
        logger.debug(f"Executing {query_obj} | params keys: {list(params.keys())}")

    async def _execute(
        self,
        query: Union[str, Neo4jQuery],
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        if isinstance(query, Neo4jQuery):
            self._log_query_execution(query)
            q, p = query.get_query(), query.get_params()
        else:
            q, p = query, params or {}
        async with self._sm.session() as s:
            result = await s.run(q, p)
            await result.consume()

    async def _fetch_all(
        self,
        query: Union[str, Neo4jQuery],
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if isinstance(query, Neo4jQuery):
            self._log_query_execution(query)
            q, p = query.get_query(), query.get_params()
        else:
            q, p = query, params or {}
        async with self._sm.session() as s:
            result = await s.run(q, p)
            return await result.data()
