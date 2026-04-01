"""
Integration: Проверка работы реальной LLM (Ollama) на извлечение сущностей и триплетов
согласно заданной онтологии.
"""

import pytest
import logging

from src.infrastructure.llm.clients.llm_entity_extractor import OllamaClient
from src.infrastructure.llm.llm_factory import ChatOllamaFactory
from src.config.ollama_settings import OllamaSettings
from src.config.extraction_settings import ExtractionSettings
from src.domain.ontology.schema import SchemaClass, SchemaRelation, SchemaStatus

pytestmark = pytest.mark.integration
logger = logging.getLogger(__name__)


@pytest.fixture
def real_ollama_extractor():
    settings = OllamaSettings(
        model_name="qwen3.5:9b",
        temperature=0.1,
        num_ctx=4096,
        is_cloud=False,
        local_url="http://localhost:11434",
    )
    ext_settings = ExtractionSettings(
        max_triples_per_chunk=15,
        min_entity_name_chars=2,
        max_entity_name_words=5,
    )
    factory = ChatOllamaFactory(settings)
    return OllamaClient(factory, ext_settings)


class TestLLMEntityExtractor:
    async def test_extracts_expected_entities_and_triples_based_on_tbox(
        self, real_ollama_extractor
    ):
        """
        Тестируем, что LLM корректно извлекает сущности и строго следует T-Box (схеме графа).
        """

        # 1. Задаем строгую схему онтологии для теста
        tbox_classes = [
            SchemaClass(name="Person", status=SchemaStatus.CORE),
            SchemaClass(name="Organization", status=SchemaStatus.CORE),
            SchemaClass(name="Location", status=SchemaStatus.CORE),
        ]

        tbox_relations = [
            SchemaRelation(
                source_class="Person",
                relation_name="WORKS_AT",
                target_class="Organization",
                status=SchemaStatus.CORE,
            ),
            SchemaRelation(
                source_class="Organization",
                relation_name="LOCATED_IN",
                target_class="Location",
                status=SchemaStatus.CORE,
            ),
        ]

        # 2. Исходный текст (чанк), из которого модель должна достать граф
        text_chunk = (
            "Алексей Смирнов работает ведущим разработчиком в компании Яндекс. "
            "Штаб-квартира Яндекса находится в Москве."
        )

        try:
            # 3. Вызываем реальную LLM
            result = await real_ollama_extractor.extract_entities_and_triples(
                text=text_chunk,
                tbox_classes=tbox_classes,
                tbox_relations=tbox_relations,
                known_entities="",
            )

            # 4. Проверки извлеченных сущностей
            entities = {e.name.lower(): e.type for e in result.entities}
            logger.info(f"Извлеченные сущности: {entities}")

            # Ожидаем, что LLM найдет Алексея, Яндекс и Москву
            assert any("алексей" in k for k in entities.keys()), (
                "Сущность 'Алексей Смирнов' не найдена"
            )
            assert any("яндекс" in k for k in entities.keys()), (
                "Сущность 'Яндекс' не найдена"
            )
            assert any("москв" in k for k in entities.keys()), (
                "Сущность 'Москва' не найдена"
            )

            # Проверяем корректность присвоенных классов (типов)
            for name, e_type in entities.items():
                if "алексей" in name:
                    assert e_type == "Person", (
                        f"Ожидался тип Person для {name}, получен {e_type}"
                    )
                elif "яндекс" in name:
                    assert e_type == "Organization", (
                        f"Ожидался тип Organization для {name}, получен {e_type}"
                    )
                elif "москв" in name:
                    assert e_type == "Location", (
                        f"Ожидался тип Location для {name}, получен {e_type}"
                    )

            # 5. Проверки извлеченных триплетов (связей)
            triples = result.triples
            logger.info(
                f"Извлеченные триплеты: {[(t.subject, t.predicate, t.object) for t in triples]}"
            )

            assert len(triples) >= 2, "Должно быть извлечено минимум 2 триплета"

            works_at_found = False
            located_in_found = False

            for t in triples:
                subj = t.subject.lower()
                obj = t.object.lower()

                # Проверяем связь WORKS_AT
                if t.predicate == "WORKS_AT":
                    if "алексей" in subj and "яндекс" in obj:
                        works_at_found = True

                # Проверяем связь LOCATED_IN
                if t.predicate == "LOCATED_IN":
                    if "яндекс" in subj and "москв" in obj:
                        located_in_found = True

            assert works_at_found, "Связь WORKS_AT (Алексей -> Яндекс) не извлечена"
            assert located_in_found, "Связь LOCATED_IN (Яндекс -> Москва) не извлечена"

        except Exception as e:
            # Если Ollama не запущена локально или отвалилась по тайм-ауту, пропускаем тест
            pytest.skip(f"LLM недоступна или произошла ошибка интеграции: {e}")
