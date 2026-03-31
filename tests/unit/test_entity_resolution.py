"""
Unit: EntityResolutionMatcher — правила матчинга сущностей.
"""

import pytest
import Levenshtein as Lev
from src.domain.resolution_rules import EntityResolutionMatcher
from src.domain.models.extraction import RawExtractedEntity
from src.domain.models.nodes import InstanceNode


@pytest.fixture
def matcher() -> EntityResolutionMatcher:
    return EntityResolutionMatcher(
        levenshtein_threshold=0.85,
        strict_name_threshold=0.95,
    )


@pytest.fixture
def candidates() -> list[InstanceNode]:
    return [
        InstanceNode(
            instance_id="id-1",
            name="Колобок",
            class_name="Product",
            chunk_id="c1",
        ),
        InstanceNode(
            instance_id="id-2",
            name="Старик",
            class_name="Person",
            chunk_id="c1",
        ),
        InstanceNode(
            instance_id="id-3",
            name="Старуха",
            class_name="Person",
            chunk_id="c1",
        ),
        InstanceNode(
            instance_id="id-4",
            name="Заяц",
            class_name="Animal",
            chunk_id="c2",
        ),
    ]


def _sim(a: str, b: str) -> float:
    """Вспомогательная: вычисляет сходство как в матчере."""
    a, b = a.strip().lower(), b.strip().lower()
    if not a or not b:
        return 0.0
    dist = Lev.distance(a, b)
    return 1.0 - dist / max(len(a), len(b))


class TestExactMatch:
    def test_exact_name_returns_match(self, matcher, candidates):
        target = RawExtractedEntity(name="Колобок", type="Product")

        result = matcher.find_best_match(target, candidates)

        assert result == "id-1"

    def test_exact_name_case_insensitive(self, matcher, candidates):
        target = RawExtractedEntity(name="колобок", type="Product")

        result = matcher.find_best_match(target, candidates)

        assert result == "id-1"


class TestStrictNameMatch:
    """Правило 2: сходство ≥ 0.95 → match без проверки типа."""

    def test_one_char_diff_in_long_name_matches(self, matcher):
        # Длина >= 20 → 1 символ разницы даёт sim >= 0.95
        cand_name = "АлександровВеликийПобедитель2025"
        target_name = (
            "АлександровВеликийПобедитель2026"  # только последняя цифра отличается
        )

        sim = _sim(target_name, cand_name)
        assert sim >= 0.95, f"Precondition: similarity={sim:.3f} must be ≥0.95"

        candidates = [
            InstanceNode(
                instance_id="id-a",
                name=cand_name,
                class_name="Person",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name=target_name, type="Location")
        result = matcher.find_best_match(target, candidates)
        assert result == "id-a"


class TestThresholdMatch:
    """Правило 3: сходство ≥ 0.85 + совпадение типа → match."""

    def test_similar_long_name_same_type_matches(self, matcher):
        # Подбираем пару с сходством ≥ 0.85 и одинаковым типом
        cand_name = "Колобочек"
        target_name = "Колобочок"
        sim = _sim(target_name, cand_name)
        assert sim >= 0.85, f"Precondition: similarity={sim:.3f} must be ≥0.85"

        candidates = [
            InstanceNode(
                instance_id="id-1",
                name=cand_name,
                class_name="Product",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name=target_name, type="Product")

        result = matcher.find_best_match(target, candidates)

        assert result == "id-1"

    def test_similar_name_different_type_no_match(self, matcher):
        cand_name = "Колобочек"
        target_name = "Колобочок"
        sim = _sim(target_name, cand_name)
        assert 0.85 <= sim < 0.95, (
            f"Precondition: sim={sim:.3f} must be in [0.85, 0.95)"
        )

        candidates = [
            InstanceNode(
                instance_id="id-1",
                name=cand_name,
                class_name="Product",
                chunk_id="c1",
            ),
        ]
        # Другой тип → правило 3 не срабатывает, правило 2 тоже (< 0.95)
        target = RawExtractedEntity(name=target_name, type="Animal")

        result = matcher.find_best_match(target, candidates)

        assert result is None

    def test_one_char_addition_same_type_matches(self, matcher):
        # "Старику" (7) vs "Старик" (6) — dist=1, max_len=7, sim=6/7≈0.857
        sim = _sim("старику", "старик")
        assert sim >= 0.85, f"Precondition: sim={sim:.3f}"

        candidates = [
            InstanceNode(
                instance_id="id-2",
                name="Старик",
                class_name="Person",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name="Старику", type="Person")

        result = matcher.find_best_match(target, candidates)

        assert result == "id-2"


class TestNoMatch:
    def test_completely_different_name_returns_none(self, matcher, candidates):
        target = RawExtractedEntity(name="Волк", type="Animal")

        result = matcher.find_best_match(target, candidates)

        assert result is None

    def test_empty_candidates_returns_none(self, matcher):
        target = RawExtractedEntity(name="Колобок", type="Product")

        result = matcher.find_best_match(target, [])

        assert result is None

    def test_short_different_names_no_match(self, matcher):
        # "Лиса" vs "Лист" — sim ≈ 0.5
        sim = _sim("лиса", "лист")
        assert sim < 0.85, f"Precondition: sim={sim:.3f} must be < 0.85"

        candidates = [
            InstanceNode(
                instance_id="id-x",
                name="Лист",
                class_name="Product",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name="Лиса", type="Animal")

        result = matcher.find_best_match(target, candidates)

        assert result is None

    def test_moderate_similarity_different_type_no_match(self, matcher):
        # "Колобка" vs "Колобок" — dist=2, sim≈0.71
        sim = _sim("колобка", "колобок")
        assert sim < 0.85, f"Precondition: sim={sim:.3f} must be < 0.85"

        candidates = [
            InstanceNode(
                instance_id="id-1",
                name="Колобок",
                class_name="Product",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name="Колобка", type="Animal")

        result = matcher.find_best_match(target, candidates)

        assert result is None


class TestDateProtection:
    """Даты не мержатся через vector search — только точное совпадение."""

    def test_exact_same_date_matches(self, matcher):
        candidates = [
            InstanceNode(
                instance_id="id-d1",
                name="2020 год",
                class_name="Date",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name="2020 год", type="Date")

        result = matcher.find_best_match(target, candidates)

        assert result == "id-d1"

    def test_similar_dates_do_not_merge(self, matcher):
        candidates = [
            InstanceNode(
                instance_id="id-d1",
                name="2010 год",
                class_name="Date",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name="2020 год", type="Date")

        result = matcher.find_best_match(target, candidates)

        assert result is None

    def test_date_with_different_format_no_merge(self, matcher):
        candidates = [
            InstanceNode(
                instance_id="id-d1",
                name="2019-2020 годы",
                class_name="Date",
                chunk_id="c1",
            ),
        ]
        target = RawExtractedEntity(name="2020 год", type="Date")

        result = matcher.find_best_match(target, candidates)

        assert result is None
