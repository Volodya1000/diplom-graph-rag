"""
Integration: Neo4jSchemaRepository — T-Box CRUD в реальном Neo4j.

Happy path + граничные случаи, которые нельзя проверить в Domain.
"""

import pytest
from src.domain.ontology.schema import SchemaClass, SchemaRelation, SchemaStatus


pytestmark = pytest.mark.integration


class TestSchemaIndexes:
    async def test_ensure_indexes_is_idempotent(self, schema_repo):
        # Двойной вызов не должен падать
        await schema_repo.ensure_indexes()

        await schema_repo.ensure_indexes()

        # Если дошли сюда — всё ок


class TestTBoxClasses:
    async def test_save_and_retrieve_classes(self, schema_repo):
        classes = [
            SchemaClass(name="Person", status=SchemaStatus.CORE, description="People"),
            SchemaClass(name="Animal", status=SchemaStatus.CORE, description="Animals"),
        ]

        await schema_repo.save_tbox_classes(classes)

        result = await schema_repo.get_tbox_classes()
        names = {c.name for c in result}
        assert "Person" in names
        assert "Animal" in names
        assert len(result) == 2

    async def test_save_class_with_parent_creates_subclass_edge(self, schema_repo):
        classes = [
            SchemaClass(name="Organization", status=SchemaStatus.CORE),
            SchemaClass(
                name="Company", status=SchemaStatus.CORE, parent="Organization"
            ),
        ]

        await schema_repo.save_tbox_classes(classes)

        result = await schema_repo.get_tbox_classes()
        company = next(c for c in result if c.name == "Company")
        assert company.parent == "Organization"

    async def test_save_empty_list_does_nothing(self, schema_repo):
        await schema_repo.save_tbox_classes([])

        result = await schema_repo.get_tbox_classes()
        assert result == []

    async def test_duplicate_save_updates_description(self, schema_repo):
        await schema_repo.save_tbox_classes(
            [
                SchemaClass(name="Person", status=SchemaStatus.CORE, description="v1"),
            ]
        )
        await schema_repo.save_tbox_classes(
            [
                SchemaClass(name="Person", status=SchemaStatus.CORE, description="v2"),
            ]
        )

        result = await schema_repo.get_tbox_classes()
        assert len(result) == 1
        assert result[0].description == "v2"


class TestSchemaRelations:
    async def test_save_and_retrieve_relations(self, schema_repo):
        await schema_repo.save_tbox_classes(
            [
                SchemaClass(name="Person", status=SchemaStatus.CORE),
                SchemaClass(name="Organization", status=SchemaStatus.CORE),
            ]
        )
        relations = [
            SchemaRelation(
                source_class="Person",
                relation_name="WORKS_AT",
                target_class="Organization",
                status=SchemaStatus.CORE,
            ),
        ]

        await schema_repo.save_schema_relations(relations)

        result = await schema_repo.get_schema_relations()
        assert len(result) == 1
        assert result[0].relation_name == "WORKS_AT"
        assert result[0].source_class == "Person"
        assert result[0].target_class == "Organization"

    async def test_relation_without_matching_classes_is_silently_skipped(
        self, schema_repo
    ):
        # Нет классов в БД — MATCH не найдёт ничего
        relations = [
            SchemaRelation(
                source_class="Phantom",
                relation_name="DOES",
                target_class="Nothing",
                status=SchemaStatus.DRAFT,
            ),
        ]

        await schema_repo.save_schema_relations(relations)

        result = await schema_repo.get_schema_relations()
        assert result == []
