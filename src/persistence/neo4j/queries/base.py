from abc import ABC, abstractmethod
from typing import Dict, Any


class Neo4jQuery(ABC):
    """Базовый класс для всех Query Objects"""

    @abstractmethod
    def get_query(self) -> str:
        """Возвращает текст Cypher-запроса"""

    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Возвращает параметры для запроса"""

    def __str__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __repr__(self) -> str:
        return self.__str__()
