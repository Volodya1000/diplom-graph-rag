"""
Реестр стратегий поиска — выбор по SearchMode.

Open/Closed: новая стратегия = register() без правки существующего кода.
"""

import logging
from typing import Dict, List

from src.domain.value_objects.search_context import SearchMode
from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy

logger = logging.getLogger(__name__)


class RetrievalStrategyRegistry:
    """
    Маппинг SearchMode → IRetrievalStrategy.
    Позволяет регистрировать стратегии динамически.
    """

    def __init__(self):
        self._strategies: Dict[SearchMode, IRetrievalStrategy] = {}

    def register(
        self,
        mode: SearchMode,
        strategy: IRetrievalStrategy,
    ) -> None:
        self._strategies[mode] = strategy
        logger.info(
            f"📌 Стратегия зарегистрирована: "
            f"{mode.value} → {strategy.name}"
        )

    def get(self, mode: SearchMode) -> IRetrievalStrategy:
        strategy = self._strategies.get(mode)
        if not strategy:
            available = [m.value for m in self._strategies]
            raise ValueError(
                f"Стратегия для '{mode.value}' не зарегистрирована. "
                f"Доступны: {available}"
            )
        return strategy

    @property
    def available_modes(self) -> List[SearchMode]:
        return list(self._strategies.keys())