"""
Unit: RetrievalStrategyRegistry — выбор стратегии по SearchMode.

Поведение:
  - Зарегистрированная стратегия возвращается
  - Незарегистрированный режим → ValueError с перечислением доступных
"""

import pytest
from src.application.services.retrieval_registry import RetrievalStrategyRegistry
from src.domain.models.search import SearchMode
from src.domain.interfaces.services.retrieval_strategy import IRetrievalStrategy


class _FakeStrategy(IRetrievalStrategy):
    def __init__(self, strategy_name: str):
        self._name = strategy_name

    @property
    def name(self) -> str:
        return self._name

    async def retrieve(self, query, query_embedding, top_k=10):
        raise NotImplementedError


class TestRetrievalRegistry:
    def test_registered_strategy_is_returned(self):
        registry = RetrievalStrategyRegistry()
        strategy = _FakeStrategy("local")
        registry.register(SearchMode.LOCAL, strategy)

        result = registry.get(SearchMode.LOCAL)

        assert result is strategy

    def test_unregistered_mode_raises_value_error(self):
        registry = RetrievalStrategyRegistry()

        with pytest.raises(ValueError, match="не зарегистрирована"):
            registry.get(SearchMode.GLOBAL)

    def test_available_modes_lists_registered(self):
        registry = RetrievalStrategyRegistry()
        registry.register(SearchMode.LOCAL, _FakeStrategy("a"))
        registry.register(SearchMode.GLOBAL, _FakeStrategy("b"))

        modes = registry.available_modes

        assert SearchMode.LOCAL in modes
        assert SearchMode.GLOBAL in modes
        assert len(modes) == 2
