import logging
import time
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.application.services.post_processing_service import PostProcessingService

logger = logging.getLogger(__name__)


class PostProcessSynonymsStep(IIngestStep):
    def __init__(self, post_processor: PostProcessingService):
        self.post_processor = post_processor

    async def execute(self, ctx: IngestContext) -> None:
        if ctx.skip_synonyms or ctx.total_entities <= 1 or not ctx.document:
            return

        t_syn = time.monotonic()
        logger.info("🔍 Post-processing: synonym resolution…")

        syn_result = await self.post_processor.resolve_synonyms(
            doc_id=ctx.document.doc_id,
            document_context=f"Документ: {ctx.file_path.name}",
        )

        logger.info(
            f"🔗 Synonyms: merged={syn_result.merged_count}, "
            f"groups={len(syn_result.groups)} "
            f"({time.monotonic() - t_syn:.1f}s)"
        )
