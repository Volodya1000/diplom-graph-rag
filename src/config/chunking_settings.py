from pydantic import BaseModel

class ChunkingSettings(BaseModel):
    tokenizer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    merge_peers: bool = True
    min_chunk_chars: int = 400
    max_chunk_chars: int = 1200
    max_heading_chars: int = 80