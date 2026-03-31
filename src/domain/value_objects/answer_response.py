"""Ответ системы на вопрос пользователя."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Ссылка на источник ответа."""

    chunk_id: str
    filename: Optional[str] = None
    chunk_index: int = 0
    relevance: float = 0.0
    start_page: int = 0
    end_page: int = 0


class AnswerResponse(BaseModel):
    """Полный ответ RAG-системы."""

    answer: str
    sources: List[SourceReference] = Field(default_factory=list)
    search_mode: str = ""
    context_stats: Dict[str, Any] = Field(default_factory=dict)
