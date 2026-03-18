"""
Use Case: Экспорт актуальной T-Box в Turtle (OWL) формат.
Только чистые классы + иерархия + объектные свойства.
Готово для Protégé.
"""
from pathlib import Path
from typing import List
import logging
from collections import defaultdict

from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.ontology.shema import SchemaClass, SchemaRelation

logger = logging.getLogger(__name__)

class ExportOntologyUseCase:
    def __init__(self, schema_repo: ISchemaRepository):
        self.schema_repo = schema_repo

    async def execute(self, output_path: Path) -> str:
        """Экспортирует онтологию и возвращает путь к файлу."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        classes = await self.schema_repo.get_tbox_classes()
        relations = await self.schema_repo.get_schema_relations()

        turtle = self._generate_turtle(classes, relations)

        output_path.write_text(turtle, encoding="utf-8")
        logger.info(f"✅ Онтология экспортирована: {output_path} "
                    f"({len(classes)} классов, {len(relations)} отношений)")
        return str(output_path)

    def _generate_turtle(
        self, classes: List[SchemaClass], relations: List[SchemaRelation]
    ) -> str:
        lines = [
            "@prefix : <http://example.org/gr_a3#> .",
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
            "# ============================================",
            "# GR_A3 Ontology — T-Box (только схема)",
            "# ============================================",
            ":gr_a3 a owl:Ontology ;",
            '    rdfs:label "GR_A3 Knowledge Graph Ontology" ;',
            '    rdfs:comment "Экспортировано из проекта gr_a3" .',
            "",
            "# ==================== КЛАССЫ ====================",
        ]

        # Сортируем: сначала CORE, потом DRAFT — это и есть "распределение по слоям"
        for cls in sorted(classes, key=lambda c: (c.status.value, c.name)):
            lines.append(f":{cls.name} a owl:Class ;")
            if cls.description:
                lines.append(f'    rdfs:comment "{cls.description.replace('"', '\\"')}" ;')
            if cls.parent:
                lines.append(f"    rdfs:subClassOf :{cls.parent} ;")
            lines.append("    .")
            lines.append("")

        # ==================== ОБЪЕКТНЫЕ СВОЙСТВА ====================
        lines.append("# ==================== ОБЪЕКТНЫЕ СВОЙСТВА ====================")

        # Группируем по имени свойства (чтобы INTERACTS_WITH и др. не дублировались)
        domains: defaultdict[str, set] = defaultdict(set)
        ranges: defaultdict[str, set] = defaultdict(set)
        comments: dict[str, str] = {}

        for rel in relations:
            name = rel.relation_name
            domains[name].add(rel.source_class)
            ranges[name].add(rel.target_class)
            if rel.description and name not in comments:
                comments[name] = rel.description

        for prop_name in sorted(domains.keys()):
            lines.append(f":{prop_name} a owl:ObjectProperty ;")
            for d in sorted(domains[prop_name]):
                lines.append(f"    rdfs:domain :{d} ;")
            for r in sorted(ranges[prop_name]):
                lines.append(f"    rdfs:range :{r} ;")
            if prop_name in comments:
                lines.append(f'    rdfs:comment "{comments[prop_name].replace('"', '\\"')}" ;')
            lines.append("    .")
            lines.append("")

        return "\n".join(lines)