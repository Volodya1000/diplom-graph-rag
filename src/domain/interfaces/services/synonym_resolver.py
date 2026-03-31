from abc import ABC, abstractmethod
from typing import List
from src.domain.models.nodes import InstanceNode
from src.domain.models.synonym import SynonymResolutionResult


class ISynonymResolver(ABC):
    @abstractmethod
    async def find_synonym_groups(
        self,
        instances: List[InstanceNode],
        document_context: str,
        text_snippets: str = "",
    ) -> SynonymResolutionResult: ...
