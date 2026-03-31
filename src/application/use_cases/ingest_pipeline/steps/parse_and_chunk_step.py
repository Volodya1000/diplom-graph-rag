import logging
import time
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.domain.models.nodes import DocumentNode, ChunkNode
from src.infrastructure.docling.doc_processor import DocProcessor

logger = logging.getLogger(__name__)


class ParseAndChunkStep(IIngestStep):
    def __init__(self, parser: DocProcessor):
        self.parser = parser

    async def execute(self, ctx: IngestContext) -> None:
        t_parse = time.monotonic()

        ctx.document = DocumentNode(filename=ctx.file_path.name)
        dl_doc = self.parser.parse_pdf(str(ctx.file_path))
        processed_chunks = self.parser.chunk_document(dl_doc)

        ctx.domain_chunks = [
            ChunkNode(
                doc_id=ctx.document.doc_id,
                chunk_index=c.metadata.chunk_index,
                text=c.enriched_text,
                headings=c.metadata.headings,
                start_page=c.metadata.start_page,
                end_page=c.metadata.end_page,
            )
            for c in processed_chunks
        ]

        logger.info(
            f"✂️ Parse + chunk: {ctx.total_chunks} chunks "
            f"({time.monotonic() - t_parse:.1f}s)"
        )
