from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    uri: str = Field(
        default="bolt://localhost:7687",
        description="URI для подключения (bolt или neo4j+s)",
    )
    user: str = Field(default="neo4j")
    password: SecretStr = Field(default=SecretStr("password"))

    # Размерность эмбеддингов — должна совпадать с моделью
    # paraphrase-multilingual-MiniLM-L12-v2 → 384
    embedding_dim: int = Field(
        default=384,
        description="Размерность вектора эмбеддинга",
    )

    # Минимальный косинусный score для vector search
    vector_search_threshold: float = Field(
        default=0.70,
        description="Порог косинусного сходства при поиске кандидатов",
    )

    @property
    def password_value(self) -> str:
        return self.password.get_secret_value()