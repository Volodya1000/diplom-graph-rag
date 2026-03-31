import logging
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository

logger = logging.getLogger(__name__)


class EnsureTBoxStep(IIngestStep):
    def __init__(self, schema_repo: ISchemaRepository):
        self.schema_repo = schema_repo

    async def execute(self, ctx: IngestContext) -> None:
        await self.schema_repo.ensure_indexes()
        current_classes = await self.schema_repo.get_tbox_classes()
        if current_classes:
            return

        logger.warning("⚠️ T-Box пуст — автоинициализация…")
        from src.domain.ontology.base_tbox import BASE_TBOX_CLASSES, BASE_TBOX_RELATIONS

        await self.schema_repo.save_tbox_classes(BASE_TBOX_CLASSES)
        await self.schema_repo.save_schema_relations(BASE_TBOX_RELATIONS)
