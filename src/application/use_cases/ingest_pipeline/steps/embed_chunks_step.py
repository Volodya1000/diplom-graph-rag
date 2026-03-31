import logging
import time
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService

logger = logging.getLogger(__name__)


class EmbedChunksStep(IIngestStep):
    def __init__(self, embedder: IEmbeddingService):
        self.embedder = embedder

    async def execute(self, ctx: IngestContext) -> None:
        if not ctx.domain_chunks:
            return

        t_embed = time.monotonic()
        embeddings = await self.embedder.embed_texts_batch(
            [c.text for c in ctx.domain_chunks],
        )
        for i, chunk in enumerate(ctx.domain_chunks):
            chunk.embedding = embeddings[i]

        logger.info(
            f"🧠 Embeddings: {len(embeddings)} ({time.monotonic() - t_embed:.1f}s)"
        )
