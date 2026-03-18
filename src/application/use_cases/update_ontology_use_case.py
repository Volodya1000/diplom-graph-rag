"""
Use Case: Обновление онтологии из TTL-файла (Protégé → Neo4j).
"""
from pathlib import Path
import logging
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.ontology.turtle_ontology_importer import TurtleOntologyImporter
from src.domain.ontology.ontology_update_validator import OntologyUpdateValidator

logger = logging.getLogger(__name__)


class UpdateOntologyUseCase:
    def __init__(self, schema_repo: ISchemaRepository):
        self.schema_repo = schema_repo

    async def execute(self, ttl_path: Path) -> dict:
        logger.info(f"📥 Импорт онтологии: {ttl_path}")

        ttl_text = ttl_path.read_text(encoding="utf-8")
        proposed_classes, proposed_relations = TurtleOntologyImporter.from_ttl(ttl_text)

        current_classes = await self.schema_repo.get_tbox_classes()
        current_relations = await self.schema_repo.get_schema_relations()
        usage = await self.schema_repo.get_class_usage_counts()

        validator = OntologyUpdateValidator()
        result = validator.validate_merge(
            current_classes, current_relations,
            proposed_classes, proposed_relations,
            usage,
        )

        if not result.is_valid:
            error_msg = "\n".join(result.errors)
            logger.error(f"❌ Валидация не пройдена:\n{error_msg}")
            raise ValueError(error_msg)

        # Merge в БД (append-only)
        await self.schema_repo.save_tbox_classes(result.merged_classes)
        await self.schema_repo.save_schema_relations(result.merged_relations)

        logger.info(
            f"✅ Онтология обновлена: "
            f"{len(result.merged_classes)} классов, "
            f"{len(result.merged_relations)} отношений"
        )
        if result.warnings:
            for w in result.warnings:
                logger.warning(f"⚠️ {w}")

        return {
            "updated_classes": len(result.merged_classes),
            "updated_relations": len(result.merged_relations),
            "warnings": result.warnings,
        }