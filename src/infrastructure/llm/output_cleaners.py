"""
Общие утилиты очистки LLM-вывода.

Используются как RunnableLambda в LangChain-цепочках.
Убирают <think>-блоки, markdown-заборы, нормализуют пробелы.
"""

import re
import logging

from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

_RE_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_RE_CODE_BLOCK = re.compile(r"```(?:json)?\s*", re.IGNORECASE)


def clean_json_output(message: AIMessage) -> str:
    """
    Очищает вывод LLM для JSON-парсинга.

    Удаляет <think>-блоки, markdown code fences.
    Возвращает строку, пригодную для PydanticOutputParser.
    """
    text = (
        message.content
        if isinstance(message, AIMessage)
        else str(message)
    )
    text = _RE_THINK.sub("", text)
    text = _RE_CODE_BLOCK.sub("", text).strip()
    if not text:
        logger.warning("⚠️ LLM вернула пустой вывод после очистки")
        return "{}"
    return text


def clean_text_output(message: AIMessage) -> str:
    """
    Очищает вывод LLM для текстовых ответов.

    Удаляет <think>-блоки, сохраняет всё остальное.
    """
    text = (
        message.content
        if isinstance(message, AIMessage)
        else str(message)
    )
    return _RE_THINK.sub("", text).strip()