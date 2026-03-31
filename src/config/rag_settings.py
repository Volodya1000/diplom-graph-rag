from pydantic import BaseModel


class RAGSettings(BaseModel):
    max_context_chars: int = 12000
    post_process_chunks_limit: int = 6
    post_process_snippet_length: int = 300
    ppr_top_k: int = 20
    ppr_damping: float = 0.85
