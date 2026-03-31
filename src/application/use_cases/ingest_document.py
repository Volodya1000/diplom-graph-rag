"""
Use Case: Полная индексация PDF → граф знаний.
Реализован через паттерн Pipeline для соблюдения SRP.
"""

import logging
import time
from pathlib import Path
from typing import List

from src.application.use_cases.ingest_pipeline.context import IngestContext, IIngestStep

logger = logging.getLogger(__name__)


class IngestDocumentUseCase:
    def __init__(self, steps: List[IIngestStep]):
        """DI-контейнер собирает и передаёт сюда готовый массив шагов."""
        self.steps = steps

    async def execute(
        self,
        file_path: Path,
        skip_synonyms: bool = False,
    ) -> str:
        t_start = time.monotonic()
        logger.info(f"📄 Start ingest pipeline: {file_path}")

        ctx = IngestContext(file_path=file_path, skip_synonyms=skip_synonyms)

        for step in self.steps:
            await step.execute(ctx)

        total_time = time.monotonic() - t_start
        avg_time = total_time / max(ctx.total_chunks, 1)

        if not ctx.document:
            raise RuntimeError("Pipeline failed: Document was not created.")

        logger.info(
            f"✅ Ingest complete: doc_id={ctx.document.doc_id}\n"
            f"   📄 File: {ctx.file_path.name}\n"
            f"   ✂️  Chunks: {ctx.total_chunks}\n"
            f"   🧩 Entities: {ctx.total_entities} (unique: {len(ctx.saved_instance_ids)})\n"
            f"   🔗 Triples: {ctx.total_triples}\n"
            f"   ⏱️  Total: {total_time:.1f}s (avg {avg_time:.1f}s/chunk)"
        )

        return ctx.document.doc_id
