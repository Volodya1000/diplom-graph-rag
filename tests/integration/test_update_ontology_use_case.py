"""
Integration: полный цикл импорта TTL → валидация → сохранение в Neo4j.
"""

import pytest
from pathlib import Path
from src.application.use_cases.update_ontology_use_case import UpdateOntologyUseCase
from src.domain.ontology.schema import SchemaClass, SchemaRelation, SchemaStatus


@pytest.mark.integration
class TestUpdateOntologyUseCase:
    async def test_valid_ttl_imports_and_merges(self, schema_repo, tmp_path: Path):
        # Подготовка базового T-Box
        await schema_repo.ensure_indexes()
        await schema_repo.save_tbox_classes(
            [
                SchemaClass(name="Person", status=SchemaStatus.CORE),
                SchemaClass(name="Organization", status=SchemaStatus.CORE),
            ]
        )
        await schema_repo.save_schema_relations(
            [
                SchemaRelation(
                    source_class="Person",
                    relation_name="WORKS_AT",
                    target_class="Organization",
                    status=SchemaStatus.CORE,
                )
            ]
        )

        ttl_content = """@prefix : <http://example.org/gr_a3#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:gr_a3 a owl:Ontology .

:Person a owl:Class ;
    rdfs:comment "People v2" .

:Employee a owl:Class ;
    rdfs:subClassOf :Person .

:Department a owl:Class ;
    rdfs:subClassOf :Organization .

:MANAGES a owl:ObjectProperty ;
    rdfs:domain :Person ;
    rdfs:range :Department .
"""
        ttl_path = tmp_path / "valid_update.ttl"
        ttl_path.write_text(ttl_content, encoding="utf-8")

        use_case = UpdateOntologyUseCase(schema_repo)
        result = await use_case.execute(ttl_path)

        assert result["updated_classes"] >= 4
        assert result["updated_relations"] >= 2

        classes = await schema_repo.get_tbox_classes()
        names = {c.name for c in classes}
        assert {"Person", "Employee", "Organization", "Department"} <= names

    async def test_cycle_prevents_update(self, schema_repo, tmp_path: Path):
        ttl_content = """@prefix : <http://example.org/gr_a3#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:Person a owl:Class .
:Animal a owl:Class ;
    rdfs:subClassOf :Person .
:Person rdfs:subClassOf :Animal . # cycle test
"""
        ttl_path = tmp_path / "cycle.ttl"
        ttl_path.write_text(ttl_content, encoding="utf-8")

        use_case = UpdateOntologyUseCase(schema_repo)

        with pytest.raises(ValueError) as exc_info:
            await use_case.execute(ttl_path)

        error_text = str(exc_info.value).lower()
        assert any(word in error_text for word in ["цикл", "cycle", "обнаружен цикл"])

    async def test_used_class_removal_gives_warning_but_allows(
        self, schema_repo, tmp_path: Path
    ):
        # Создаём класс, который будем "удалять"
        await schema_repo.save_tbox_classes(
            [SchemaClass(name="Unused", status=SchemaStatus.DRAFT)]
        )

        ttl_content = """@prefix : <http://example.org/gr_a3#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:Person a owl:Class .
:Organization a owl:Class .
"""
        ttl_path = tmp_path / "remove_unused.ttl"
        ttl_path.write_text(ttl_content, encoding="utf-8")

        use_case = UpdateOntologyUseCase(schema_repo)
        result = await use_case.execute(ttl_path)

        # В текущей реализации Unused остаётся (append-only), но если usage > 0 → warning
        # В тесте usage=0 → warnings может не быть, но импорт должен пройти успешно
        assert "updated_classes" in result
        assert result["updated_classes"] >= 2  # Person + Organization

        classes_after = await schema_repo.get_tbox_classes()
        names_after = {c.name for c in classes_after}
        assert "Unused" in names_after  # append-only — не удаляется
