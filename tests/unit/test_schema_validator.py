"""
Unit: SchemaValidator — иерархия классов и валидация отношений.

Поведение:
  - Отношение Person→WORKS_AT→Organization допустимо
  - Подкласс Employee наследует отношения Person
  - Подкласс Company наследует отношения Organization
  - Несуществующее отношение отклоняется
"""

import pytest
from src.domain.ontology.shema import SchemaClass, SchemaRelation, SchemaStatus
from src.domain.ontology.schema_validator import SchemaValidator


class TestSchemaValidatorHierarchy:

    def test_direct_relation_is_allowed(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        result = validator.is_relation_allowed("Person", "WORKS_AT", "Organization")

        assert result is True

    def test_child_inherits_parent_source_relation(self, base_classes, base_relations):
        # Employee ⊂ Person, поэтому Employee→WORKS_AT→Organization допустимо
        validator = SchemaValidator(base_classes, base_relations)

        result = validator.is_relation_allowed("Employee", "WORKS_AT", "Organization")

        assert result is True

    def test_child_inherits_parent_target_relation(self, base_classes, base_relations):
        # Company ⊂ Organization, поэтому Person→WORKS_AT→Company допустимо
        validator = SchemaValidator(base_classes, base_relations)

        result = validator.is_relation_allowed("Person", "WORKS_AT", "Company")

        assert result is True

    def test_both_children_inherit_relation(self, base_classes, base_relations):
        # Employee ⊂ Person, Company ⊂ Organization
        validator = SchemaValidator(base_classes, base_relations)

        result = validator.is_relation_allowed("Employee", "WORKS_AT", "Company")

        assert result is True

    def test_nonexistent_relation_is_rejected(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        result = validator.is_relation_allowed("Person", "EATS", "Animal")

        assert result is False

    def test_reversed_relation_is_rejected(self, base_classes, base_relations):
        # WORKS_AT: Person→Organization, но не Organization→Person
        validator = SchemaValidator(base_classes, base_relations)

        result = validator.is_relation_allowed("Organization", "WORKS_AT", "Person")

        assert result is False

    def test_predicate_is_case_insensitive(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        result = validator.is_relation_allowed("Person", "works_at", "Organization")

        assert result is True


class TestSchemaValidatorAncestors:

    def test_root_class_has_only_itself(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        ancestors = validator.get_ancestors("Person")

        assert ancestors == {"Person"}

    def test_child_class_includes_parent(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        ancestors = validator.get_ancestors("Company")

        assert ancestors == {"Company", "Organization"}

    def test_unknown_class_returns_empty(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        ancestors = validator.get_ancestors("UnknownClass")

        assert ancestors == set()


class TestSchemaValidatorFormatting:

    def test_hierarchy_tree_contains_all_roots(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        tree = validator.format_hierarchy_tree()

        assert "Person" in tree
        assert "Organization" in tree
        assert "Animal" in tree

    def test_hierarchy_tree_shows_children(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        tree = validator.format_hierarchy_tree()

        assert "Company" in tree
        assert "Employee" in tree

    def test_format_relations_contains_all(self, base_classes, base_relations):
        validator = SchemaValidator(base_classes, base_relations)

        formatted = validator.format_relations()

        assert "WORKS_AT" in formatted
        assert "LOCATED_IN" in formatted
        assert "INTERACTS_WITH" in formatted

    def test_empty_relations_returns_placeholder(self, base_classes):
        validator = SchemaValidator(base_classes, [])

        formatted = validator.format_relations()

        assert "не заданы" in formatted