"""
Unit: TurtleOntologyExporter (домен) + UseCase.
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from src.domain.ontology.turtle_ontology_exporter import TurtleOntologyExporter
from src.application.use_cases.export_ontology import ExportOntologyUseCase
from src.domain.ontology.shema import SchemaClass  # для теста escaping

pytestmark = pytest.mark.unit


class TestTurtleOntologyExporter:
    def test_core_classes_first_then_draft(self, base_classes):
        turtle = TurtleOntologyExporter.to_turtle(base_classes, [])
        assert turtle.find(":Person") < turtle.find(":Employee")

    def test_class_with_parent_has_subClassOf(self, base_classes):
        turtle = TurtleOntologyExporter.to_turtle(base_classes, [])
        assert "rdfs:subClassOf :Organization" in turtle

    def test_property_has_domain_and_range(self, base_relations):
        turtle = TurtleOntologyExporter.to_turtle([], base_relations)
        for rel in base_relations:
            assert f":{rel.relation_name} a owl:ObjectProperty" in turtle
            assert f"rdfs:domain :{rel.source_class}" in turtle
            assert f"rdfs:range :{rel.target_class}" in turtle

    def test_comment_escaping(self):
        classes = [SchemaClass(name="Test", description='Текст с "кавычками"')]
        turtle = TurtleOntologyExporter.to_turtle(classes, [])
        assert 'rdfs:comment "Текст с \\"кавычками\\""' in turtle


class TestExportOntologyUseCase:
    async def test_use_case_delegates_to_domain(self, tmp_path: Path):
        # Мок репозитория
        mock_repo = AsyncMock()
        mock_repo.get_tbox_classes.return_value = []
        mock_repo.get_schema_relations.return_value = []

        use_case = ExportOntologyUseCase(mock_repo)
        file = tmp_path / "test.ttl"

        saved_path = await use_case.execute(file)

        assert file.exists()
        content = file.read_text(encoding="utf-8")
        assert "@prefix : <http://example.org/gr_a3#>" in content
        assert str(saved_path) == str(file)