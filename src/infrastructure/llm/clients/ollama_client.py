import re
from re import Pattern

import logging
from typing import List

from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage

from src.domain.interfaces.llm.llm_client import ILLMClient
from src.domain.models import SchemaClass, RawExtractedEntity
from src.config.ollama_settings import OllamaSettings
from src.infrastructure.llm.prompts.entity_extraction import get_entity_extraction_prompt

logger = logging.getLogger(__name__)


# --- Внутренние DTO для парсера ---

class _ParsedEntity(BaseModel):
    name: str
    type: str


class _ExtractedEntities(BaseModel):
    entities: List[_ParsedEntity]


# --- Утилита очистки вывода LLM ---

_RE_THINK: Pattern[str] = re.compile(r"<think>.*?</think>", re.DOTALL)
_RE_CODE_BLOCK: Pattern[str] = re.compile(r"```(?:json)?\s*", re.IGNORECASE)

def _clean_llm_output(message: AIMessage) -> str:
    text = message.content if isinstance(message, AIMessage) else str(message)
    text = _RE_THINK.sub("", text)        # type: ignore[arg-type]
    text = _RE_CODE_BLOCK.sub("", text)   # type: ignore[arg-type]
    text = text.strip()
    if not text:
        logger.warning("⚠️ LLM вернула пустой ответ или только <think> теги.")
        return '{"entities": []}'
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

    @staticmethod
    def _format_tbox(tbox_schema: List[SchemaClass]) -> str:
        if not tbox_schema:
            return "(типы не заданы — определи подходящие типы самостоятельно)"
        lines = []
        for cls in tbox_schema:
            desc = f" — {cls.description}" if cls.description else ""
            lines.append(f"• {cls.name}{desc}")
        return "\n".join(lines)

    async def extract_entities(
            self, text: str, tbox_schema: List[SchemaClass]
    ) -> List[RawExtractedEntity]:

        tbox_str = self._format_tbox(tbox_schema)

        logger.info(f"📨 LLM input text size: {len(text)} chars")
        logger.debug(f"📨 TBOX:\n{tbox_str}")

        parser = PydanticOutputParser(pydantic_object=_ExtractedEntities)
        prompt: ChatPromptTemplate = get_entity_extraction_prompt()

        prompt = prompt.partial(
            format_instructions=parser.get_format_instructions()
        )

        chain = (
                prompt
                | self.llm
                | RunnableLambda(_clean_llm_output)
                | parser
        )

        try:
            parsed: _ExtractedEntities = await chain.ainvoke({
                "tbox_schema": tbox_str,
                "text": text,
            })

            entities: List[RawExtractedEntity] = [
                RawExtractedEntity(
                    name=item.name.strip(),
                    type=item.type.strip(),
                )
                for item in parsed.entities
                if item.name and item.type
            ]

            logger.info(f"🤖 LLM extracted entities: {len(entities)}")
            if entities:
                logger.debug(
                    f"🤖 Entities: {[f'{e.name} [{e.type}]' for e in entities]}"
                )

            return entities

        except Exception as e:
            logger.exception(f"❌ LLM extraction failed: {e}")
            return []