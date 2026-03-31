import logging
import time
from tqdm import tqdm
from pathlib import Path
from typing import List
from src.application.use_cases.ingest_pipeline.context import IngestContext, IIngestStep

logger = logging.getLogger(__name__)


class IngestDocumentUseCase:
    def __init__(self, steps: List[IIngestStep]):
        self.steps = steps

    async def execute(
        self,
        file_path: Path,
        skip_synonyms: bool = False,
    ) -> str:
        t_start = time.monotonic()
        logger.info(f"📄 Запуск пайплайна индексации: {file_path.name}")

        ctx = IngestContext(file_path=file_path, skip_synonyms=skip_synonyms)

        # Красивый прогресс-бар для всего пайплайна
        for step_idx, step in enumerate(
            tqdm(self.steps, desc="🚀 Индексация", unit="шаг"), 1
        ):
            step_name = step.__class__.__name__.replace("Step", "")
            logger.info(f"[{step_idx}/{len(self.steps)}] Выполняется шаг: {step_name}")

            await step.execute(ctx)

        total_time = time.monotonic() - t_start
        avg_time = total_time / max(ctx.total_chunks, 1)

        logger.info(
            f"🎉 Индексация успешно завершена!\n"
            f"   📄 Документ: {ctx.file_path.name}\n"
            f"   ✂️ Чанков: {ctx.total_chunks}\n"
            f"   🧩 Сущностей: {ctx.total_entities} (уникальных: {len(ctx.saved_instance_ids)})\n"
            f"   🔗 Триплетов: {ctx.total_triples}\n"
            f"   ⏱️ Общее время: {total_time:.1f} сек (в среднем {avg_time:.1f} сек/чанк)"
        )

        if not ctx.document:
            raise RuntimeError("Pipeline failed: Document was not created.")

        return ctx.document.doc_id
