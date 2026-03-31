import logging
from typing import Dict, List
from src.domain.models.search import SearchMode
from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy

logger = logging.getLogger(__name__)


class RetrievalStrategyRegistry:
    def __init__(self):
        self._strategies: Dict[SearchMode, IRetrievalStrategy] = {}

    def register(self, mode: SearchMode, strategy: IRetrievalStrategy) -> None:
        self._strategies[mode] = strategy
        logger.info(f"📌 Стратегия зарегистрирована: {mode.value} → {strategy.name}")

    def get(self, mode: SearchMode) -> IRetrievalStrategy:
        strategy = self._strategies.get(mode)
        if not strategy:
            available = [m.value for m in self._strategies]
            raise ValueError(
                f"Стратегия для '{mode.value}' не зарегистрирована. Доступны: {available}"
            )
        return strategy

    @property
    def available_modes(self) -> List[SearchMode]:
        return list(self._strategies.keys())
