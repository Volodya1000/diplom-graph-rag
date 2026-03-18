"""
Unit: нормализация предикатов.

Поведение: строка с пробелами, дефисами, спецсимволами → UPPER_SNAKE_CASE.
"""

from src.domain.utils.normalize_predicate import normalize_predicate


class TestNormalizePredicate:

    def test_simple_predicate_converted_to_upper(self):
        result = normalize_predicate("works_at")

        assert result == "WORKS_AT"

    def test_spaces_replaced_with_underscores(self):
        result = normalize_predicate("works at")

        assert result == "WORKS_AT"

    def test_hyphens_replaced_with_underscores(self):
        result = normalize_predicate("located-in")

        assert result == "LOCATED_IN"

    def test_special_characters_removed(self):
        result = normalize_predicate("works@at!")

        assert result == "WORKSAT"

    def test_mixed_spaces_and_hyphens(self):
        result = normalize_predicate("part - of")

        assert result == "PART_OF"

    def test_empty_string_returns_related_to(self):
        result = normalize_predicate("")

        assert result == "RELATED_TO"

    def test_only_special_chars_returns_related_to(self):
        result = normalize_predicate("@#$%")

        assert result == "RELATED_TO"

    def test_already_normalized_stays_same(self):
        result = normalize_predicate("INTERACTS_WITH")

        assert result == "INTERACTS_WITH"

    def test_leading_trailing_whitespace_stripped(self):
        result = normalize_predicate("  knows  ")

        assert result == "KNOWS"