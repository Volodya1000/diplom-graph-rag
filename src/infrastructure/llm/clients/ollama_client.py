"""
LLM-клиент на базе Ollama: извлечение сущностей + троек.
"""

import re
import logging
from re import Pattern
from typing import List

from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage

from src.domain.interfaces.llm.llm_client import ILLMClient
from src.domain.models import (
    SchemaClass, SchemaRelation,
    ExtractionResult, RawExtractedEntity, RawExtractedTriple,
)
from src.domain.ontology.schema_validator import SchemaValidator
from src.config.ollama_settings import OllamaSettings
from src.infrastructure.llm.prompts.entity_extraction import (
    get_entity_extraction_prompt,
)

logger = logging.getLogger(__name__)


# ---- Внутренние DTO для PydanticOutputParser ----

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


# ---- Утилита очистки вывода LLM ----

_RE_THINK: Pattern[str] = re.compile(r"<think>.*?</think>", re.DOTALL)
_RE_CODE_BLOCK: Pattern[str] = re.compile(
    r"```(?:json)?\s*", re.IGNORECASE
)


def _clean_llm_output(message: AIMessage) -> str:
    text = (
        message.content
        if isinstance(message, AIMessage)
        else str(message)
    )
    text = _RE_THINK.sub("", text)
    text = _RE_CODE_BLOCK.sub("", text)
    text = text.strip()
    if not text:
        logger.warning("⚠️ LLM вернула пустой ответ")
        return '{"entities": [], "triples": []}'
    return text


class OllamaClient(ILLMClient):
    def __init__(self, settings: OllamaSettings):
        self.settings = settings
        self.llm = self._create_chat_ollama(settings)

    def _create_chat_ollama(self, settings: OllamaSettings) -> ChatOllama:
        url = settings.base_url
        logger.info(
            f"🔌 LLM init | model={settings.model_name} "
            f"| cloud={settings.is_cloud} | url={url}"
        )
        return ChatOllama(
            model=settings.model_name,
            base_url=url,
            temperature=settings.temperature,
            num_ctx=settings.num_ctx,
            client_kwargs={"headers": settings.headers},
            format="json",
            verbose=False,
        )

    # ------------------------------------------------------------------
    async def extract_entities_and_triples(
        self,
        text: str,
        tbox_classes: List[SchemaClass],
        tbox_relations: List[SchemaRelation],
    ) -> ExtractionResult:

        # Форматируем схему для промпта
        validator = SchemaValidator(tbox_classes, tbox_relations)
        classes_str = validator.format_hierarchy_tree()
        relations_str = validator.format_relations()

        logger.info(f"📨 LLM input: {len(text)} chars")
        logger.debug(f"📨 Classes:\n{classes_str}")
        logger.debug(f"📨 Relations:\n{relations_str}")

        parser = PydanticOutputParser(pydantic_object=_ExtractionOutput)
        prompt: ChatPromptTemplate = get_entity_extraction_prompt()
        prompt = prompt.partial(
            format_instructions=parser.get_format_instructions(),
        )

        chain = (
            prompt
            | self.llm
            | RunnableLambda(_clean_llm_output)
            | parser
        )

        try:
            parsed: _ExtractionOutput = await chain.ainvoke({
                "tbox_classes": classes_str,
                "tbox_relations": relations_str,
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
                f"🤖 LLM result: {len(entities)} entities, "
                f"{len(triples)} triples"
            )

            return ExtractionResult(entities=entities, triples=triples)

        except Exception as e:
            logger.exception(f"❌ LLM extraction failed: {e}")
            return ExtractionResult()