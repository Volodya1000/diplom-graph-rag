from typing import Optional

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
        description="URI для подключения (bolt или neo4j+s)"
    )
    user: str = Field(
        default="neo4j",
        description="Имя пользователя"
    )
    password: SecretStr = Field(
        default=SecretStr("password"),
        description="Пароль"
    )

    @property
    def password_value(self) -> str:
        """Безопасное извлечение пароля"""
        return self.password.get_secret_value()