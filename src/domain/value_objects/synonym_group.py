"""Группа синонимов — результат LLM-анализа."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SynonymGroup(BaseModel):
    """Группа сущностей, которые обозначают одно и то же."""
    canonical_name: str
    canonical_type: str
    aliases: List[str] = Field(default_factory=list)
    instance_ids: List[str] = Field(default_factory=list)
    reason: str = ""


class SynonymResolutionResult(BaseModel):
    """Результат LLM-анализа синонимов по документу."""
    groups: List[SynonymGroup] = Field(default_factory=list)
    merged_count: int = 0
    kept_count: int = 0