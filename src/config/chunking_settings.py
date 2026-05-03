from pydantic import BaseModel


class ChunkingSettings(BaseModel):
    tokenizer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_tokens: int = 100  # Максимальный размер чанка (под размер контекста модели)
    merge_peers: bool = True  # Разрешаем слияние соседних списков/абзацев
    max_heading_chars: int = 10
