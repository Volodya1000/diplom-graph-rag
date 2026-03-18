"""
Unit-тесты: все бизнес-правила валидации и merge.
"""
import pytest
from src.domain.ontology.ontology_update_validator import (
    OntologyUpdateValidator,
    ValidationResult,
)
from src.domain.ontology.shema import SchemaClass, SchemaRelation, SchemaStatus


@pytest.fixture
def validator():
    return OntologyUpdateValidator()


@pytest.fixture
def current_classes():
    return [
        SchemaClass(name="Person", status=SchemaStatus.CORE),
        SchemaClass(name="Organization", status=SchemaStatus.CORE),
        SchemaClass(name="Employee", status=SchemaStatus.DRAFT, parent="Person"),
    ]


@pytest.fixture
def current_relations():
    return [
        SchemaRelation(
            source_class="Person", relation_name="WORKS_AT",
            target_class="Organization", status=SchemaStatus.CORE
        ),
    ]


class TestMergeLogic:
    def test_new_class_added(self, validator, current_classes, current_relations):
        proposed = current_classes + [
            SchemaClass(name="Department", status=SchemaStatus.DRAFT, parent="Organization")
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            proposed, current_relations,
            class_usage={}
        )
        assert result.is_valid
        assert len(result.merged_classes) == 4
        assert "Department" in {c.name for c in result.merged_classes}

    def test_existing_class_description_updated(self, validator, current_classes, current_relations):
        proposed = [
            SchemaClass(name="Person", status=SchemaStatus.DRAFT, description="Люди v2"),
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            proposed, current_relations,
            class_usage={}
        )
        person = next(c for c in result.merged_classes if c.name == "Person")
        assert person.description == "Люди v2"


class TestCycleDetection:
    def test_cycle_detected(self, validator, current_classes, current_relations):
        proposed = current_classes + [
            SchemaClass(name="Animal", status=SchemaStatus.DRAFT, parent="Person"),
            SchemaClass(name="Person", status=SchemaStatus.DRAFT, parent="Animal"),  # цикл
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            proposed, current_relations,
            class_usage={}
        )
        assert not result.is_valid
        # Подгоняем под реальное сообщение из твоего кода
        assert "Обнаружен цикл в иерархии классов" in " ".join(result.errors)

    def test_no_cycle_self_reference(self, validator, current_classes, current_relations):
        proposed = current_classes + [
            SchemaClass(name="Manager", status=SchemaStatus.DRAFT, parent="Manager"),  # сам на себя
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            proposed, current_relations,
            class_usage={}
        )
        assert not result.is_valid
        assert "Обнаружен цикл" in " ".join(result.errors)


class TestIntegrity:
    def test_missing_parent_rejected(self, validator, current_classes, current_relations):
        proposed = current_classes + [
            SchemaClass(name="Intern", status=SchemaStatus.DRAFT, parent="Student"),  # нет Student
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            proposed, current_relations,
            class_usage={}
        )
        assert not result.is_valid
        assert "Родитель" in " ".join(result.errors)
        assert "Student" in " ".join(result.errors)

    def test_relation_with_missing_class_rejected(self, validator, current_classes, current_relations):
        proposed_rels = current_relations + [
            SchemaRelation(
                source_class="Student", relation_name="STUDIES_AT",
                target_class="University"
            )
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            current_classes, proposed_rels,
            class_usage={}
        )
        assert not result.is_valid
        assert "ссылается на несуществующий класс" in " ".join(result.errors)


class TestDeletionProtection:
    def test_used_class_not_deleted_warning(self, validator, current_classes, current_relations):
        result = validator.validate_merge(
            current_classes, current_relations,
            [current_classes[0]],  # только Person остался
            current_relations,
            class_usage={"Organization": 15, "Employee": 3}
        )
        assert result.is_valid  # валидно, но с предупреждением
        assert len(result.warnings) >= 1
        warnings_text = " ".join(result.warnings)
        assert "Organization" in warnings_text or "Employee" in warnings_text

    def test_unused_class_can_be_deleted_no_warning(self, validator, current_classes, current_relations):
        result = validator.validate_merge(
            current_classes, current_relations,
            [current_classes[0]],  # убрали Organization и Employee
            current_relations,
            class_usage={"Organization": 0, "Employee": 0}
        )
        assert result.is_valid
        assert not result.warnings


class TestNamingRules:
    def test_invalid_class_name_rejected(self, validator, current_classes, current_relations):
        proposed = current_classes + [
            SchemaClass(name="123Person", status=SchemaStatus.DRAFT),
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            proposed, current_relations,
            class_usage={}
        )
        assert not result.is_valid
        assert "Неверный формат класса" in " ".join(result.errors)
        assert "123Person" in " ".join(result.errors)

    def test_invalid_relation_name_rejected(self, validator, current_classes, current_relations):
        proposed_rels = current_relations + [
            SchemaRelation(
                source_class="Person", relation_name="works-at",  # не UPPER_SNAKE
                target_class="Organization"
            )
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            current_classes, proposed_rels,
            class_usage={}
        )
        assert not result.is_valid
        assert "Неверный формат отношения" in " ".join(result.errors)
        assert "works-at" in " ".join(result.errors)


class TestNoSelfReference:
    def test_self_referencing_relation_rejected(self, validator, current_classes, current_relations):
        proposed_rels = current_relations + [
            SchemaRelation(
                source_class="Person", relation_name="KNOWS",
                target_class="Person"
            )
        ]
        result = validator.validate_merge(
            current_classes, current_relations,
            current_classes, proposed_rels,
            class_usage={}
        )
        assert not result.is_valid
        assert "Самоссылка" in " ".join(result.errors)