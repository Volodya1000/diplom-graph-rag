from pydantic import BaseModel, Field
from typing import Set, List


class ExtractionSettings(BaseModel):
    max_entity_name_words: int = 5
    max_entity_name_chars: int = 60
    min_entity_name_chars: int = 2
    max_triples_per_chunk: int = 15

    no_vector_merge_types: Set[str] = Field(default_factory=lambda: {"date", "event"})

    strict_allowed_relations: bool = True

    # Пороги для Entity Resolution
    levenshtein_threshold: float = 0.85
    strict_name_threshold: float = 0.95
    semantic_similarity_threshold: float = 0.88

    # Стоп-слова для мусорных сущностей
    entity_stop_words: List[str] = Field(
        default_factory=lambda: [
            "введение",
            "заключение",
            "глава",
            "рисунок",
            "таблица",
        ]
    )
