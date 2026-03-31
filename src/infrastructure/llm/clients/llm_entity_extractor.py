import logging
from typing import List
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
from src.config.extraction_settings import ExtractionSettings
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.domain.models.extraction import (
    ExtractionResult,
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
        self, factory: ChatOllamaFactory, extraction_settings: ExtractionSettings
    ):
        self._llm = factory.create_json(temperature=0.4)
        self._settings = extraction_settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _invoke_chain(self, chain, params: dict) -> _ExtractionOutput:
        return await chain.ainvoke(params)

    async def extract_entities_and_triples(
        self,
        text: str,
        tbox_classes: List[SchemaClass],
        tbox_relations: List[SchemaRelation],
        known_entities: str = "",
    ) -> ExtractionResult:
        validator = SchemaValidator(tbox_classes, tbox_relations)
        parser = PydanticOutputParser(pydantic_object=_ExtractionOutput)
        prompt = get_entity_extraction_prompt().partial(
            format_instructions=parser.get_format_instructions()
        )
        chain = prompt | self._llm | RunnableLambda(clean_json_output) | parser

        try:
            parsed = await self._invoke_chain(
                chain,
                {
                    "tbox_classes": validator.format_hierarchy_tree(),
                    "tbox_relations": validator.format_relations(),
                    "known_entities": known_entities or "(пока нет)",
                    "text": text,
                },
            )

            entities = [
                RawExtractedEntity(name=e.name.strip(), type=e.type.strip())
                for e in parsed.entities
                if e.name.strip()
                and e.type.strip()
                and not self._is_bad_entity(e.name.strip())
            ]
            valid_names = {e.name.lower() for e in entities}

            triples = []
            for t in parsed.triples:
                subj, pred, obj = (
                    t.subject.strip(),
                    t.predicate.strip(),
                    t.object.strip(),
                )
                if (
                    subj
                    and pred
                    and obj
                    and (subj.lower() in valid_names or subj in known_entities)
                    and (obj.lower() in valid_names or obj in known_entities)
                ):
                    triples.append(
                        RawExtractedTriple(subject=subj, predicate=pred, object=obj)
                    )

            if len(triples) > self._settings.max_triples_per_chunk:
                triples = triples[: self._settings.max_triples_per_chunk]

            return ExtractionResult(entities=entities, triples=triples)

        except Exception as e:
            logger.exception(f"❌ LLM extraction failed: {e}")
            return ExtractionResult()

    def _is_bad_entity(self, name: str) -> bool:
        name_lower = name.lower()
        stop_words = {
            "введение",
            "заключение",
            "глава",
            "рисунок",
            "современные направления",
        }
        if name_lower in stop_words:
            return True
        s = self._settings
        if len(name) < s.min_entity_name_chars or len(name) > s.max_entity_name_chars:
            return True
        if len(name.split()) > s.max_entity_name_words:
            return True
        if len(name.split()) == 1 and name[0].islower() and name.isalpha():
            return True
        return False
