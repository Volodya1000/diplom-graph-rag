from pydantic import BaseModel

class ChunkingSettings(BaseModel):
    tokenizer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    merge_peers: bool = True