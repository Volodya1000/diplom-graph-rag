import logging
from typing import cast, Any

from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.domain.interfaces.services.synonym_resolver import ISynonymResolver
from src.domain.models.nodes import InstanceNode
from src.domain.models.synonym import SynonymGroup, SynonymResolutionResult
from src.infrastructure.llm.llm_factory import ChatModelFactory
from src.infrastructure.llm.prompts.synonym_resolution import (
    get_synonym_resolution_prompt,
)

logger = logging.getLogger(__name__)


class _SynonymGroupParsed(BaseModel):
    canonical: str = Field(description="Каноническое (основное) имя сущности")
    canonical_type: str = Field(default="", description="Тип сущности")
    synonyms: list[str] = Field(default_factory=list, description="Список синонимов")
    reason: str = Field(default="", description="Причина объединения")


class _SynonymOutput(BaseModel):
    groups: list[_SynonymGroupParsed] = Field(default_factory=list)


class OllamaSynonymResolver(ISynonymResolver):
    def __init__(self, factory: ChatModelFactory):
        self._llm = factory.create_json(temperature=0.1)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(cast(Any, logger), logging.WARNING),
        reraise=True,
    )
    async def _invoke_chain(self, chain: Runnable, params: dict) -> _SynonymOutput:
        return await chain.ainvoke(params)

    async def find_synonym_groups(
        self,
        instances: list[InstanceNode],
        document_context: str,
        text_snippets: str = "",
    ) -> SynonymResolutionResult:
        if len(instances) < 2:
            return SynonymResolutionResult()

        seen, entity_lines, id_by_name = set(), [], {}
        for inst in instances:
            key = (inst.name.lower(), inst.class_name.lower())
            if key not in seen:
                seen.add(key)
                entity_lines.append(f"• {inst.name} [{inst.class_name}]")
            id_by_name.setdefault(inst.name.lower(), []).append(inst.instance_id)

        structured_llm = self._llm.with_structured_output(
            _SynonymOutput,
            method="json_mode",
        )
        prompt = get_synonym_resolution_prompt()

        chain = prompt | structured_llm

        try:
            parsed: _SynonymOutput = await self._invoke_chain(
                chain,
                {
                    "document_context": document_context,
                    "text_snippets": text_snippets,
                    "entities_list": "\n".join(entity_lines),
                },
            )

            groups = []
            for g in parsed.groups:
                if not g.canonical.strip() or not g.synonyms:
                    continue
                all_ids = {
                    iid for name in [g.canonical, *g.synonyms] for iid in id_by_name.get(name.strip().lower(), [])
                }
                groups.append(
                    SynonymGroup(
                        canonical_name=g.canonical.strip(),
                        canonical_type=g.canonical_type,
                        aliases=[a.strip() for a in g.synonyms],
                        instance_ids=list(all_ids),
                        reason=g.reason,
                    ),
                )

            merged = sum(len(g.aliases) for g in groups)
            return SynonymResolutionResult(
                groups=groups,
                merged_count=merged,
                kept_count=len(entity_lines) - merged,
            )

        except Exception as e:
            logger.exception(f"❌ Synonym resolution failed: {e}")
            return SynonymResolutionResult()
