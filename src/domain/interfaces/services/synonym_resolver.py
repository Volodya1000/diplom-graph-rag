from abc import ABC, abstractmethod

from src.domain.models.nodes import InstanceNode
from src.domain.models.synonym import SynonymResolutionResult


class ISynonymResolver(ABC):
    @abstractmethod
    async def find_synonym_groups(
        self,
        instances: list[InstanceNode],
        document_context: str,
        text_snippets: str = "",
    ) -> SynonymResolutionResult: ...
