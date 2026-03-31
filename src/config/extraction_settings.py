from pydantic import BaseModel, Field


class ExtractionSettings(BaseModel):
    max_entity_name_words: int = 5
    max_entity_name_chars: int = 60
    min_entity_name_chars: int = 2
    max_triples_per_chunk: int = 15
    no_vector_merge_types: set[str] = Field(default_factory=lambda: {"date"})

    # Пороги для Entity Resolution
    levenshtein_threshold: float = 0.85
    strict_name_threshold: float = 0.95
