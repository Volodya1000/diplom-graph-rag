"""
Unit: EntityRegistry — кросс-чанковый кеш сущностей.

Поведение:
  - Новая сущность регистрируется и находится
  - Повторная регистрация того же имени — игнорируется (first wins)
  - Поиск по похожему имени (Левенштейн) работает
  - format_known_entities для LLM-контекста
"""

import pytest
from src.application.services.entity_resolution_service import EntityRegistry
from src.domain.graph_components.nodes import InstanceNode


@pytest.fixture
def registry() -> EntityRegistry:
    return EntityRegistry(levenshtein_threshold=0.85)


@pytest.fixture
def kolobok() -> InstanceNode:
    return InstanceNode(
        instance_id="id-1", name="Колобок",
        class_name="Product", chunk_id="c1",
    )


class TestRegistration:

    def test_registered_entity_is_found(self, registry, kolobok):
        registry.register("Колобок", kolobok)

        result = registry.find("Колобок")

        assert result is not None
        assert result.instance_id == "id-1"

    def test_first_registration_wins(self, registry, kolobok):
        second = InstanceNode(
            instance_id="id-2", name="Колобок",
            class_name="Animal", chunk_id="c2",
        )

        registry.register("Колобок", kolobok)
        registry.register("Колобок", second)
        result = registry.find("Колобок")

        assert result.instance_id == "id-1"
        assert result.class_name == "Product"

    def test_search_is_case_insensitive(self, registry, kolobok):
        registry.register("Колобок", kolobok)

        result = registry.find("колобок")

        assert result is not None
        assert result.instance_id == "id-1"


class TestFuzzySearch:

    def test_similar_name_found_by_levenshtein(self, registry, kolobok):
        registry.register("Колобок", kolobok)

        result = registry.find("Колобоk")  # 1 символ разницы

        assert result is not None
        assert result.instance_id == "id-1"

    def test_very_different_name_not_found(self, registry, kolobok):
        registry.register("Колобок", kolobok)

        result = registry.find("Волк")

        assert result is None


class TestFormatting:

    def test_empty_registry_returns_empty_string(self, registry):
        result = registry.format_known_entities()

        assert result == ""

    def test_format_includes_registered_entities(self, registry, kolobok):
        registry.register("Колобок", kolobok)
        starik = InstanceNode(
            instance_id="id-2", name="Старик",
            class_name="Person", chunk_id="c1",
        )
        registry.register("Старик", starik)

        result = registry.format_known_entities()

        assert "Колобок [Product]" in result
        assert "Старик [Person]" in result

    def test_all_instances_returns_registered(self, registry, kolobok):
        registry.register("Колобок", kolobok)

        result = registry.all_instances

        assert len(result) == 1
        assert result[0].name == "Колобок"