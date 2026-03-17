"""Промпт для генерации ответа на вопрос (RAG QA)."""

from langchain_core.prompts import ChatPromptTemplate

DEFAULT_QA_SYSTEM_PROMPT = (
    "Ты — экспертная QA-система. "
    "Отвечай на вопрос ТОЛЬКО на основе предоставленного контекста. "
    "Если информации недостаточно — скажи об этом честно. "
    "Цитируй факты из контекста. Отвечай на русском."
)


def get_answer_generation_prompt(
    system_prompt: str = DEFAULT_QA_SYSTEM_PROMPT,
) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", (
            "=== КОНТЕКСТ ===\n{context}\n\n"
            "=== ВОПРОС ===\n{question}\n\n"
            "Ответ:"
        )),
    ])