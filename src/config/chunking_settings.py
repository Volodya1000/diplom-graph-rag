from pydantic import BaseModel


class ChunkingSettings(BaseModel):
    tokenizer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    merge_peers: bool = True
    min_chunk_chars: int = 50    # минимум символов
    max_heading_chars: int = 80  # максимум для заголовка в контексте