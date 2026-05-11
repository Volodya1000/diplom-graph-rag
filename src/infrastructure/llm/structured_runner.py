import logging
from typing import Any, Type, TypeVar, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import BasePromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.infrastructure.llm.output_cleaners import clean_json_output

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


class StructuredOutputRunner:
    """
    Инфраструктурная утилита для генерации структурированных ответов.
    Обеспечивает DRY для ретраев и fallback-парсинга JSON (особенно важно для Ollama).
    """

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(cast(Any, logger), logging.WARNING),
        reraise=True,
    )
    async def execute(
        self,
        prompt_template: BasePromptTemplate,
        output_model: Type[TModel],
        params: dict[str, Any],
    ) -> TModel:
        parser = PydanticOutputParser(pydantic_object=output_model)

        # Инжектим инструкции формата только если промпт их ожидает
        if "format_instructions" in prompt_template.input_variables:
            params["format_instructions"] = parser.get_format_instructions()

        # Надежная цепочка с ручной очисткой мусора от локальных моделей
        chain = prompt_template | self._llm | RunnableLambda(clean_json_output) | parser

        return await chain.ainvoke(params)
