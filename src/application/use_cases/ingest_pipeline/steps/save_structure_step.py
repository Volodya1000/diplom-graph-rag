import logging
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.domain.services.builders.edge_builder import GraphEdgeBuilder
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository

logger = logging.getLogger(__name__)


class SaveDocumentStructureStep(IIngestStep):
    def __init__(self, doc_repo: IDocumentRepository, edge_repo: IEdgeRepository):
        self.doc_repo = doc_repo
        self.edge_repo = edge_repo

    async def execute(self, ctx: IngestContext) -> None:
        if not ctx.document or not ctx.domain_chunks:
            return

        await self.doc_repo.save_document(ctx.document)
        for chunk in ctx.domain_chunks:
            await self.doc_repo.save_chunk(chunk)

        edges = GraphEdgeBuilder.build_document_edges(
            document=ctx.document, chunks=ctx.domain_chunks
        )
        await self.edge_repo.save_edges(edges)

        logger.info(f"💾 Документ + {ctx.total_chunks} чанков сохранены")
