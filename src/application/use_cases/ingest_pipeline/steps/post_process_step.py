import logging
import time
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.application.services.post_processing_service import PostProcessingService

logger = logging.getLogger(__name__)


class PostProcessSynonymsStep(IIngestStep):
    def __init__(self, post_processor: PostProcessingService):
        self.post_processor = post_processor

    async def execute(self, ctx: IngestContext) -> None:
        if ctx.skip_synonyms:
            logger.info("⏭️ Постобработка синонимов пропущена (--skip-synonyms)")
            return

        if ctx.total_entities <= 1 or not ctx.document:
            logger.info("⏭️ Постобработка синонимов не нужна (мало сущностей)")
            return

        t_syn = time.monotonic()
        logger.info("🔍 Запуск постобработки: поиск синонимов...")

        syn_result = await self.post_processor.resolve_synonyms(
            doc_id=ctx.document.doc_id,
            document_context=f"Документ: {ctx.file_path.name}",
        )

        duration = time.monotonic() - t_syn

        if syn_result.groups:
            logger.info(
                f"🔗 Синонимы обработаны за {duration:.1f}с | "
                f"групп: {len(syn_result.groups)} | "
                f"объединено: {syn_result.merged_count}"
            )

            for i, group in enumerate(syn_result.groups, 1):
                logger.info(
                    f"   Группа {i}: «{group.canonical_name}» ← {group.aliases}"
                )
        else:
            logger.info(
                f"✅ Постобработка завершена за {duration:.1f}с (синонимов не найдено)"
            )
