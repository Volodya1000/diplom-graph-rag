from pydantic import BaseModel, Field


class ExtractionSettings(BaseModel):
    """
    Настройки постфильтрации извлечённых сущностей.

    Все правила — структурные, не зависят от языка или домена.
    """

    # Длина имени
    max_entity_name_words: int = Field(
        default=5,
        description="Максимум слов в имени сущности",
    )
    max_entity_name_chars: int = Field(
        default=60,
        description="Максимум символов в имени сущности",
    )
    min_entity_name_chars: int = Field(
        default=2,
        description="Минимум символов в имени сущности",
    )

    # Тройки
    max_triples_per_chunk: int = Field(
        default=15,
        description="Максимум троек на один чанк",
    )

    # Типы, которые не мержатся через vector search
    no_vector_merge_types: set[str] = Field(
        default_factory=lambda: {"date"},
        description="Типы сущностей, для которых запрещён fuzzy merge",
    )