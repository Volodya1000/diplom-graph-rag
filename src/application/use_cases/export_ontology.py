"""
Use Case: Экспорт онтологии.
Теперь — только оркестратор. Вся логика в домене.
"""
from pathlib import Path
import logging

from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.ontology.turtle_ontology_exporter import TurtleOntologyExporter

logger = logging.getLogger(__name__)


class ExportOntologyUseCase:
    """Тонкий use-case — только делегирует домену."""

    def __init__(self, schema_repo: ISchemaRepository):
        self.schema_repo = schema_repo

    async def execute(self, output_path: Path) -> str:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        classes = await self.schema_repo.get_tbox_classes()
        relations = await self.schema_repo.get_schema_relations()

        turtle = TurtleOntologyExporter.to_turtle(classes, relations)

        output_path.write_text(turtle, encoding="utf-8")
        logger.info(f"✅ Онтология экспортирована: {output_path} "
                    f"({len(classes)} классов, {len(relations)} отношений)")
        return str(output_path)