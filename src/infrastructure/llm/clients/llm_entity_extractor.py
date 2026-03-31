"""
LLM-клиент: извлечение сущностей + троек.

Исправлено: before_sleep_log типизация через cast.
"""

import logging
from typing import List, cast

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
from tenacity._utils import LoggerProtocol

from src.config.extraction_settings import ExtractionSettings
from src.domain.interfaces.llm.llm_client import ILLMClient, ExtractionResult
from src.application.dtos.extraction_dtos import (
    RawExtractedEntity,
    RawExtractedTriple,
)
from src.domain.ontology.schema import SchemaClass, SchemaRelation
from src.domain.ontology.schema_validator import SchemaValidator
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.infrastructure.llm.output_cleaners import clean_json_output
from src.infrastructure.llm.prompts.entity_extraction import (
    get_entity_extraction_prompt,
)

logger = logging.getLogger(__name__)
_tenacity_logger = cast(LoggerProtocol, logger)


class _ParsedEntity(BaseModel):
    name: str
    type: str


class _ParsedTriple(BaseModel):
    subject: str
    predicate: str
    object: str


class _ExtractionOutput(BaseModel):
    entities: List[_ParsedEntity] = Field(default_factory=list)
    triples: List[_ParsedTriple] = Field(default_factory=list)


class OllamaClient(ILLMClient):
    def __init__(
        self,
        factory: ChatOllamaFactory,
        extraction_settings: ExtractionSettings,
    ):
        self._llm = factory.create_json(temperature=0.4)
        self._settings = extraction_settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(_tenacity_logger, logging.WARNING),
        reraise=True,
    )
    async def _invoke_chain(self, chain, params: dict) -> _ExtractionOutput:  # type: ignore[type-arg]
        return await chain.ainvoke(params)

    async def extract_entities_and_triples(
        self,
        text: str,
        tbox_classes: List[SchemaClass],
        tbox_relations: List[SchemaRelation],
        known_entities: str = "",
    ) -> ExtractionResult:

        validator = SchemaValidator(tbox_classes, tbox_relations)
        classes_str = validator.format_hierarchy_tree()
        relations_str = validator.format_relations()
        known_str = known_entities if known_entities else "(пока нет)"

        logger.info(f"📨 LLM input: {len(text)} chars")

        parser = PydanticOutputParser(pydantic_object=_ExtractionOutput)
        prompt = get_entity_extraction_prompt()
        prompt = prompt.partial(
            format_instructions=parser.get_format_instructions(),
        )

        chain = prompt | self._llm | RunnableLambda(clean_json_output) | parser

        try:
            parsed: _ExtractionOutput = await self._invoke_chain(
                chain,
                {
                    "tbox_classes": classes_str,
                    "tbox_relations": relations_str,
                    "known_entities": known_str,
                    "text": text,
                },
            )

            entities = []
            filtered_count = 0
            for e in parsed.entities:
                name = e.name.strip()
                etype = e.type.strip()
                if not name or not etype:
                    continue
                if self._is_bad_entity(name):
                    logger.debug(f"🚫 Filtered entity: «{name}»")
                    filtered_count += 1
                    continue
                entities.append(RawExtractedEntity(name=name, type=etype))

            if filtered_count > 0:
                logger.info(
                    f"🚫 Filtered: {filtered_count} entities "
                    f"(of {len(parsed.entities)} raw)"
                )

            valid_names = {e.name.lower() for e in entities}

            triples = []
            for t in parsed.triples:
                subj = t.subject.strip()
                pred = t.predicate.strip()
                obj = t.object.strip()
                if not subj or not pred or not obj:
                    continue
                if subj.lower() not in valid_names and subj not in known_str:
                    continue
                if obj.lower() not in valid_names and obj not in known_str:
                    continue
                triples.append(
                    RawExtractedTriple(
                        subject=subj,
                        predicate=pred,
                        object=obj,
                    )
                )

            trimmed = len(parsed.triples) - len(triples)
            if trimmed > 0:
                logger.info(
                    f"✂️ Trimmed: {trimmed} triples (of {len(parsed.triples)} raw)"
                )

            max_t = self._settings.max_triples_per_chunk
            if len(triples) > max_t:
                logger.warning(f"⚠️ Capped triples: {len(triples)} → {max_t}")
                triples = triples[:max_t]

            logger.info(f"🤖 LLM: {len(entities)} entities, {len(triples)} triples")
            return ExtractionResult(entities=entities, triples=triples)

        except Exception as e:
            logger.exception(f"❌ LLM extraction failed after retries: {e}")
            return ExtractionResult()

    def _is_bad_entity(self, name: str) -> bool:
        s = self._settings
        if len(name) < s.min_entity_name_chars:
            return True
        if len(name) > s.max_entity_name_chars:
            return True
        words = name.split()
        if len(words) > s.max_entity_name_words:
            return True
        if len(words) == 1 and name[0].islower() and name.isalpha():
            return True
        return False
