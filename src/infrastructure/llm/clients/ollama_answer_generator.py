"""LLM-генератор ответов на вопросы."""

import logging
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.config.ollama_settings import OllamaSettings

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM = (
    "Ты — экспертная QA-система. "
    "Отвечай на вопрос ТОЛЬКО на основе предоставленного контекста. "
    "Если информации недостаточно — скажи об этом честно. "
    "Цитируй факты из контекста. Отвечай на русском."
)


class OllamaAnswerGenerator(IAnswerGenerator):
    def __init__(self, settings: OllamaSettings):
        self._llm = ChatOllama(
            model=settings.model_name,
            base_url=settings.base_url,
            temperature=0.3,
            num_ctx=settings.num_ctx,
            client_kwargs={"headers": settings.headers},
        )

    async def generate(
        self,
        question: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt or _DEFAULT_SYSTEM),
            ("human", (
                "=== КОНТЕКСТ ===\n{context}\n\n"
                "=== ВОПРОС ===\n{question}\n\n"
                "Ответ:"
            )),
        ])

        chain = prompt | self._llm
        try:
            result = await chain.ainvoke({
                "context": context,
                "question": question,
            })
            return result.content
        except Exception as e:
            logger.exception(f"❌ Генерация ответа: {e}")
            return f"Ошибка генерации ответа: {e}"