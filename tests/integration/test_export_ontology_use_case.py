"""
Integration: ExportOntologyUseCase + реальный репозиторий.
"""
import pytest
from pathlib import Path
from src.application.use_cases.export_ontology import ExportOntologyUseCase
from src.domain.ontology.shema import SchemaClass, SchemaRelation, SchemaStatus


pytestmark = pytest.mark.integration


class TestExportOntologyIntegration:
    async def test_export_creates_valid_file_with_real_data(self, schema_repo, tmp_path: Path):
        await schema_repo.ensure_indexes()
        await schema_repo.save_tbox_classes([
            SchemaClass(name="Person", status=SchemaStatus.CORE, description="Люди"),
            SchemaClass(name="Employee", status=SchemaStatus.DRAFT, parent="Person"),
            SchemaClass(name="Organization", status=SchemaStatus.CORE, description="Организации"),
        ])
        await schema_repo.save_schema_relations([
            SchemaRelation(
                source_class="Person",
                relation_name="WORKS_AT",
                target_class="Organization",
                status=SchemaStatus.CORE,
                description="Работает в организации",
            ),
        ])

        use_case = ExportOntologyUseCase(schema_repo)
        output_file = tmp_path / "gr_a3_real.ttl"

        await use_case.execute(output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        assert ":Person a owl:Class" in content
        assert "rdfs:subClassOf :Person" in content
        assert ":Organization a owl:Class" in content
        assert ":WORKS_AT a owl:ObjectProperty" in content