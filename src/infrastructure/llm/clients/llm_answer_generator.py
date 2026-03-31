"""
LLM-генератор ответов на вопросы.
"""

import logging
from typing import Optional

from langchain_core.runnables import RunnableLambda

from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.infrastructure.llm.output_cleaners import clean_text_output
from src.infrastructure.llm.prompts.answer_generation import (
    get_answer_generation_prompt,
)

logger = logging.getLogger(__name__)


class OllamaAnswerGenerator(IAnswerGenerator):
    def __init__(self, factory: ChatOllamaFactory):
        self._llm = factory.create_text(temperature=0.3)

    async def generate(
        self,
        question: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        prompt = get_answer_generation_prompt(
            system_prompt=system_prompt,
        ) if system_prompt else get_answer_generation_prompt()

        chain = (
            prompt
            | self._llm
            | RunnableLambda(clean_text_output)
        )

        try:
            result: str = await chain.ainvoke({
                "context": context,
                "question": question,
            })
            return result

        except Exception as e:
            logger.exception(f"❌ Генерация ответа: {e}")
            return f"Ошибка генерации ответа: {e}"