from sentence_transformers import SentenceTransformer
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
import numpy as np
from typing import List
import asyncio


class SentenceTransformerService(IEmbeddingService):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    async def embed_text(self, text: str) -> List[float]:
        embedding = await asyncio.to_thread(self.model.encode, text)
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        return embedding.tolist()

    async def embed_texts_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = await asyncio.to_thread(self.model.encode, texts)
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
        return embeddings.tolist()