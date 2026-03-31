from abc import ABC, abstractmethod
from typing import Dict, Any, Generic, TypeVar

T = TypeVar("T")


class Neo4jQuery(ABC, Generic[T]):
    """Базовый класс для всех Query Objects с типизацией возвращаемого значения."""

    @abstractmethod
    def get_query(self) -> str:
        """Возвращает текст Cypher-запроса"""

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Возвращает параметры для запроса"""

    @abstractmethod
    def map_record(self, record: Dict[str, Any]) -> T:
        """Маппит строку результата (Neo4j Record) в доменный объект T"""

    def __str__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __repr__(self) -> str:
        return self.__str__()
