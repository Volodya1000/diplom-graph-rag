"""LLM-резолвер синонимов."""

import logging
from typing import Dict, List,cast
from tenacity._utils import LoggerProtocol

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from src.domain.interfaces.services.synonym_resolver import ISynonymResolver
from src.domain.graph_components.nodes import InstanceNode
from src.domain.value_objects.synonym_group import (
    SynonymGroup,
    SynonymResolutionResult,
)
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.infrastructure.llm.output_cleaners import clean_json_output
from src.infrastructure.llm.prompts.synonym_resolution import (
    get_synonym_resolution_prompt,
)

logger = logging.getLogger(__name__)
_tenacity_logger = cast(LoggerProtocol, logger)


class _SynonymGroupParsed(BaseModel):
    canonical_name: str
    canonical_type: str = ""
    aliases: List[str] = Field(default_factory=list)
    reason: str = ""


class _SynonymOutput(BaseModel):
    groups: List[_SynonymGroupParsed] = Field(default_factory=list)


class OllamaSynonymResolver(ISynonymResolver):
    def __init__(self, factory: ChatOllamaFactory):
        self._llm = factory.create_json(temperature=0.1)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
        reraise=True,
    )
    async def _invoke_chain(self, chain, params: dict) -> _SynonymOutput:  # type: ignore[type-arg]
        return await chain.ainvoke(params)

    async def find_synonym_groups(
        self,
        instances: List[InstanceNode],
        document_context: str,
        text_snippets: str = "",
    ) -> SynonymResolutionResult:
        if len(instances) < 2:
            return SynonymResolutionResult()

        seen: set = set()
        entity_lines: List[str] = []
        id_by_name: Dict[str, List[str]] = {}

        for inst in instances:
            key = (inst.name.lower(), inst.class_name.lower())
            if key not in seen:
                seen.add(key)
                entity_lines.append(
                    f"• {inst.name} [{inst.class_name}]"
                )
            id_by_name.setdefault(
                inst.name.lower(), [],
            ).append(inst.instance_id)

        logger.info(
            f"🔍 Synonym analysis: "
            f"{len(entity_lines)} unique entities"
        )

        parser = PydanticOutputParser(pydantic_object=_SynonymOutput)
        prompt = get_synonym_resolution_prompt()
        prompt = prompt.partial(
            format_instructions=parser.get_format_instructions(),
        )

        chain = (
            prompt
            | self._llm
            | RunnableLambda(clean_json_output)
            | parser
        )

        try:
            parsed: _SynonymOutput = await self._invoke_chain(
                chain,
                {
                    "document_context": document_context,
                    "text_snippets": text_snippets or "(нет)",
                    "entities_list": "\n".join(entity_lines),
                },
            )

            groups = self._build_groups(parsed, id_by_name)
            merged = sum(len(g.aliases) for g in groups)

            logger.info(
                f"🔗 Synonym groups: {len(groups)}, "
                f"to merge: {merged} entities"
            )

            return SynonymResolutionResult(
                groups=groups,
                merged_count=merged,
                kept_count=len(entity_lines) - merged,
            )

        except Exception as e:
            logger.exception(f"❌ Synonym resolution failed: {e}")
            return SynonymResolutionResult()

    @staticmethod
    def _build_groups(
        parsed: _SynonymOutput,
        id_by_name: Dict[str, List[str]],
    ) -> List[SynonymGroup]:
        groups: List[SynonymGroup] = []
        for g in parsed.groups:
            canonical = g.canonical_name.strip()
            if not canonical:
                continue
            aliases = [a.strip() for a in g.aliases if a.strip()]
            if not aliases:
                continue
            all_ids: set = set()
            for name_variant in [canonical] + aliases:
                for iid in id_by_name.get(name_variant.lower(), []):
                    all_ids.add(iid)
            groups.append(SynonymGroup(
                canonical_name=canonical,
                canonical_type=g.canonical_type,
                aliases=aliases,
                instance_ids=list(all_ids),
                reason=g.reason,
            ))
        return groups