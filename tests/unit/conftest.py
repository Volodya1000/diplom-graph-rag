"""
Фикстуры для unit-тестов.

Здесь создаются доменные объекты — никаких внешних зависимостей.
"""

import pytest
from src.domain.ontology.shema import SchemaClass, SchemaRelation, SchemaStatus


@pytest.fixture
def base_classes() -> list[SchemaClass]:
    """Минимальный набор классов для тестов."""
    return [
        SchemaClass(name="Person", status=SchemaStatus.CORE, description="People"),
        SchemaClass(name="Organization", status=SchemaStatus.CORE, description="Orgs"),
        SchemaClass(name="Location", status=SchemaStatus.CORE, description="Places"),
        SchemaClass(name="Animal", status=SchemaStatus.CORE, description="Animals"),
        SchemaClass(name="Product", status=SchemaStatus.CORE, description="Products"),
        SchemaClass(
            name="Company", status=SchemaStatus.CORE,
            description="Companies", parent="Organization",
        ),
        SchemaClass(
            name="Employee", status=SchemaStatus.DRAFT,
            description="Employees", parent="Person",
        ),
    ]


@pytest.fixture
def base_relations() -> list[SchemaRelation]:
    """Минимальный набор отношений для тестов."""
    return [
        SchemaRelation(
            source_class="Person", relation_name="WORKS_AT",
            target_class="Organization", status=SchemaStatus.CORE,
        ),
        SchemaRelation(
            source_class="Person", relation_name="LOCATED_IN",
            target_class="Location", status=SchemaStatus.CORE,
        ),
        SchemaRelation(
            source_class="Animal", relation_name="INTERACTS_WITH",
            target_class="Person", status=SchemaStatus.CORE,
        ),
        SchemaRelation(
            source_class="Person", relation_name="CREATED",
            target_class="Product", status=SchemaStatus.CORE,
        ),
    ]