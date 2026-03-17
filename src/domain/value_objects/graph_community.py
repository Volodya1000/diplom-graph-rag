"""Сообщество в графе (результат community detection)."""

from typing import List, Optional
from pydantic import BaseModel, Field


class GraphCommunity(BaseModel):
    """Хранимое сообщество с предрассчитанной сводкой."""
    community_id: int
    level: int = 0                                    # иерархия Leiden
    member_ids: List[str] = Field(default_factory=list)
    summary: Optional[str] = None                     # LLM-generated
    key_entities: List[str] = Field(default_factory=list)
    entity_count: int = 0