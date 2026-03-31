import yaml
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from src.config.chunking_settings import ChunkingSettings
from src.config.extraction_settings import ExtractionSettings
from src.config.neo4j_settings import Neo4jSettings
from src.config.ollama_settings import OllamaSettings
from src.config.parsing_settings import ParsingSettings
from src.config.rag_settings import RAGSettings


class AppSettings(BaseSettings):
    """
    Корневой класс настроек.
    Использует Pydantic V2 BaseSettings.
    Принимает базовые данные из YAML, а затем Pydantic АВТОМАТИЧЕСКИ
    переопределяет их переменными из .env (по правилу env_nested_delimiter).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    embedding_model: str

    neo4j: Neo4jSettings
    ollama: OllamaSettings
    chunking: ChunkingSettings
    parsing: ParsingSettings
    extraction: ExtractionSettings
    rag: RAGSettings = RAGSettings()


def load_config(yaml_path: str = "config.yml") -> AppSettings:
    """
    Фабрика конфигурации.
    1. Читает несекретные данные из YAML.
    2. Передает их в AppSettings.
    3. AppSettings сам подтягивает секреты из .env.
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Файл конфигурации {yaml_path} не найден.")

    with open(path, "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f) or {}

    return AppSettings(**yaml_data)