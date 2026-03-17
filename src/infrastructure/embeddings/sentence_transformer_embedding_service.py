import asyncio
from typing import List
from sentence_transformers import SentenceTransformer
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService

class SentenceTransformerService(IEmbeddingService):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    async def embed_text(self, text: str) -> List[float]:
        embedding = await asyncio.to_thread(self.model.encode, text)
        return embedding.tolist()

    async def embed_texts_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = await asyncio.to_thread(self.model.encode, texts)
        return embeddings.tolist()