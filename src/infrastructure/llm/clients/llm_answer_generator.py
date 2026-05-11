# src/infrastructure/llm/answer_generator.py
import logging
from typing import TypeVar, Type

from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from src.infrastructure.llm.structured_runner import StructuredOutputRunner
from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.infrastructure.llm.llm_factory import ChatModelFactory
from src.infrastructure.llm.output_cleaners import clean_text_output
from src.infrastructure.llm.prompts.answer_generation import (
    get_answer_generation_prompt,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaAnswerGenerator(IAnswerGenerator):
    def __init__(self, factory: ChatModelFactory):
        self._factory = factory
        # Используем текстовый режим (не JSON)
        self._llm = factory.create_text(temperature=0.3)
        self._structured_runner = StructuredOutputRunner(factory.create_json(temperature=0.1))

    async def generate(
        self,
        question: str,
        context: str,
        system_prompt: str | None = None,
    ) -> str:
        prompt = (
            get_answer_generation_prompt(system_prompt=system_prompt)
            if system_prompt
            else get_answer_generation_prompt()
        )
        chain = prompt | self._llm | RunnableLambda(clean_text_output)

        try:
            result: str = await chain.ainvoke(
                {
                    "context": context,
                    "question": question,
                },
            )
            return result
        except Exception as e:
            logger.exception(f"❌ Генерация ответа: {e}")
            return f"Ошибка генерации ответа: {e}"

    async def generate_structured(
        self,
        question: str,
        context: str,
        output_model: Type[T],
        system_prompt: str | None = None,
    ) -> T:
        prompt = (
            get_answer_generation_prompt(system_prompt=system_prompt)
            if system_prompt
            else get_answer_generation_prompt()
        )

        try:
            return await self._structured_runner.execute(
                prompt_template=prompt,
                output_model=output_model,
                params={
                    "context": context,
                    "question": question,
                },
            )
        except Exception as e:
            logger.exception(f"❌ Генерация структурированного ответа: {e}")
            raise
