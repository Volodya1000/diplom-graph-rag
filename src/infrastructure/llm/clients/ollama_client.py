"""
LLM-клиент: извлечение сущностей + троек.
"""

import logging
from typing import List

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda

from src.domain.interfaces.llm.llm_client import ILLMClient, ExtractionResult
from src.application.dtos.extraction_dtos import (
    RawExtractedEntity,
    RawExtractedTriple,
)
from src.domain.ontology.shema import SchemaClass, SchemaRelation
from src.domain.ontology.schema_validator import SchemaValidator
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.infrastructure.llm.output_cleaners import clean_json_output
from src.infrastructure.llm.prompts.entity_extraction import (
    get_entity_extraction_prompt,
)

logger = logging.getLogger(__name__)


# ---- Внутренние DTO для парсера ----

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
    def __init__(self, factory: ChatOllamaFactory):
        self._llm = factory.create_json(temperature=0.4)

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

        chain = (
            prompt
            | self._llm
            | RunnableLambda(clean_json_output)
            | parser
        )

        try:
            parsed: _ExtractionOutput = await chain.ainvoke({
                "tbox_classes": classes_str,
                "tbox_relations": relations_str,
                "known_entities": known_str,
                "text": text,
            })

            entities = [
                RawExtractedEntity(
                    name=e.name.strip(),
                    type=e.type.strip(),
                )
                for e in parsed.entities
                if e.name and e.type
            ]
            triples = [
                RawExtractedTriple(
                    subject=t.subject.strip(),
                    predicate=t.predicate.strip(),
                    object=t.object.strip(),
                )
                for t in parsed.triples
                if t.subject and t.predicate and t.object
            ]

            logger.info(
                f"🤖 LLM: {len(entities)} entities, "
                f"{len(triples)} triples"
            )
            return ExtractionResult(entities=entities, triples=triples)

        except Exception as e:
            logger.exception(f"❌ LLM extraction failed: {e}")
            return ExtractionResult()