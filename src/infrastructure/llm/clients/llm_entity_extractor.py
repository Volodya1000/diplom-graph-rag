import logging
import re

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel, Field
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
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
from src.infrastructure.llm.llm_factory import ChatModelFactory
from src.infrastructure.llm.output_cleaners import clean_json_output
from src.infrastructure.llm.prompts.entity_extraction import (
    get_entity_extraction_prompt,
)

logger = logging.getLogger(__name__)


# ==================== МОДЕЛИ ПАРСИНГА (Pydantic) ====================
class _ParsedEntity(BaseModel):
    name: str
    type: str


class _ParsedTriple(BaseModel):
    subject: str
    predicate: str
    object: str


class _ExtractionOutput(BaseModel):
    entities: list[_ParsedEntity] = Field(default_factory=list)
    triples: list[_ParsedTriple] = Field(default_factory=list)


# ==================== КЛИЕНТ ====================
class OllamaClient(ILLMClient):
    _CAMEL_CASE_RE = re.compile(r"^[А-Я][а-я]+[А-Я][а-яA-ZА-Я0-9]+$")

    def __init__(self, factory: ChatModelFactory, extraction_settings: ExtractionSettings):
        # Используем JSON-режим для извлечения структур
        self._llm = factory.create_json(temperature=0.1)
        self._settings = extraction_settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _invoke_chain(self, chain: Runnable, params: dict):
        return await chain.ainvoke(params)

    async def extract_entities_and_triples(
        self,
        text: str,
        tbox_classes: list[SchemaClass],
        tbox_relations: list[SchemaRelation],
        known_entities: str = "",
    ) -> ExtractionResult:
        """Точка входа. Оркестратор: получает данные, валидирует, возвращает результат."""
        try:
            # 1. Получаем сырые распарсенные данные от LLM
            parsed_data = await self._run_extraction_chain(text, tbox_classes, tbox_relations, known_entities)

            # 2. Обрабатываем сущности
            entities, valid_names = self._process_entities(parsed_data.entities)

            # 3. Обрабатываем триплеты на основе валидных сущностей
            triples = self._process_triples(parsed_data.triples, valid_names, known_entities)

            return ExtractionResult(entities=entities, triples=triples)

        except Exception as e:
            logger.exception(f"❌ LLM extraction failed: {e}")
            return ExtractionResult()

    # --- Приватные методы (Инкапсуляция и SRP) ---

    async def _run_extraction_chain(
        self,
        text: str,
        classes: list[SchemaClass],
        relations: list[SchemaRelation],
        known_entities: str,
    ) -> _ExtractionOutput:
        """Инкапсулирует логику создания и вызова цепочки LangChain."""
        validator = SchemaValidator(classes, relations)
        parser = PydanticOutputParser(pydantic_object=_ExtractionOutput)

        prompt = get_entity_extraction_prompt().partial(format_instructions=parser.get_format_instructions())

        chain = prompt | self._llm | RunnableLambda(clean_json_output) | parser

        return await self._invoke_chain(
            chain,
            {
                "tbox_classes": validator.format_hierarchy_tree(),
                "tbox_relations": validator.format_relations(),
                "known_entities": known_entities or "(пока нет)",
                "text": text,
            },
        )

    def _process_entities(self, raw_entities: list[_ParsedEntity]) -> tuple[list[RawExtractedEntity], set[str]]:
        """Фильтрует сущности и собирает сет валидных имен."""
        valid_entities = []
        valid_names_lower = set()

        for e in raw_entities:
            name, entity_type = e.name.strip(), e.type.strip()

            if name and entity_type and not self._is_bad_entity(name):
                valid_entities.append(RawExtractedEntity(name=name, type=entity_type))
                valid_names_lower.add(name.lower())

        return valid_entities, valid_names_lower

    def _process_triples(
        self,
        raw_triples: list[_ParsedTriple],
        valid_names: set[str],
        known_entities: str,
    ) -> list[RawExtractedTriple]:
        """Фильтрует триплеты и применяет лимиты."""
        valid_triples = []

        for t in raw_triples:
            subj, pred, obj = t.subject.strip(), t.predicate.strip(), t.object.strip()

            if not (subj and pred and obj):
                continue

            # KISS: Выносим сложные проверки в отдельные переменные
            subj_is_valid = (subj.lower() in valid_names) or (subj in known_entities)
            obj_is_valid = (obj.lower() in valid_names) or (obj in known_entities)

            if subj_is_valid and obj_is_valid:
                valid_triples.append(RawExtractedTriple(subject=subj, predicate=pred, object=obj))

        # Применяем лимит из настроек (срез списка безопасен, даже если элементов меньше)
        limit = self._settings.max_triples_per_chunk
        return valid_triples[:limit]

    def _is_bad_entity(self, name: str) -> bool:
        """Проверяет сущность на галлюцинации и мусор."""
        s = self._settings

        if len(name) < s.min_entity_name_chars or len(name) > s.max_entity_name_chars:
            return True

        if len(name.split()) > s.max_entity_name_words:
            return True

        if len(name.split()) == 1 and name[0].islower() and name.isalpha():
            return True

        return bool(" " not in name and self._CAMEL_CASE_RE.match(name) and len(name) > 12)
