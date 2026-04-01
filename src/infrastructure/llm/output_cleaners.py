"""
Общие утилиты очистки LLM-вывода.
"""

import re
import logging
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)

# Регулярки для очистки мыслей (теги <think>) и лишнего markdown
_RE_THINK: re.Pattern[str] = re.compile(r"<think>.*?</think>", re.DOTALL)
_RE_CODE_BLOCK: re.Pattern[str] = re.compile(r"```(?:json)?\s*", re.IGNORECASE)


def clean_json_output(message: AIMessage) -> str:
    """Очищает JSON от тегов <think> и Markdown-блоков."""
    text: str = (
        message.content
        if isinstance(message, AIMessage) and isinstance(message.content, str)
        else str(message)
    )
    text = _RE_THINK.sub("", text)
    text = _RE_CODE_BLOCK.sub("", text).replace("```", "").strip()

    if not text:
        logger.warning("⚠️ LLM вернула пустой вывод после очистки")
        return "{}"
    return text


def clean_text_output(message: AIMessage) -> str:
    """Очищает обычный текст от тегов <think>."""
    text: str = (
        message.content
        if isinstance(message, AIMessage) and isinstance(message.content, str)
        else str(message)
    )
    return _RE_THINK.sub("", text).strip()
