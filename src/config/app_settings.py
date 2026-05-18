from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Annotated, Any, Union

import yaml
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config.chunking_settings import ChunkingSettings
from src.config.extraction_settings import ExtractionSettings
from src.config.neo4j_settings import Neo4jSettings
from src.config.ollama_settings import OllamaSettings
from src.config.parsing_settings import ParsingSettings
from src.config.rag_settings import RAGSettings
from src.config.vllm_settings import VLLMSettings

LLMSettingsType = Annotated[
    Union[OllamaSettings, VLLMSettings],
    Field(discriminator="provider"),
]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    embedding_model: str

    api_host: str = "0.0.0.0"
    api_port: int = 8001

    @computed_field
    @property
    def api_base_url(self) -> str:
        host = "localhost" if self.api_host == "0.0.0.0" else self.api_host
        return f"http://{host}:{self.api_port}"

    neo4j: Neo4jSettings
    llm: LLMSettingsType
    chunking: ChunkingSettings
    parsing: ParsingSettings
    extraction: ExtractionSettings
    rag: RAGSettings = RAGSettings()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Файл конфигурации {path} не найден.")

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)

    return result


def load_config(
    yaml_path: str | Path = "config.yml",
    override_path: str | Path | None = None,
) -> AppSettings:
    """Загружает базовый YAML и при необходимости накладывает override."""
    root = _project_root()

    base_file = Path(yaml_path)
    if not base_file.is_absolute():
        base_file = root / base_file

    data = _load_yaml(base_file)

    if override_path is not None:
        override_file = Path(override_path)
        if not override_file.is_absolute():
            override_file = root / override_file

        override_data = _load_yaml(override_file)
        data = _deep_merge(data, override_data)

    return AppSettings(**data)
