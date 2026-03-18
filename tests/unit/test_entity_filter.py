"""
Unit: постфильтрация сущностей — структурные правила.

Поведение:
  - Слишком короткое имя → отклоняется
  - Слишком длинное имя (символы/слова) → отклоняется
  - Одно строчное слово → отклоняется (нарицательное)
  - Одно слово с заглавной → проходит (имя собственное)
  - Аббревиатуры → проходят
  - Многословные имена в пределах лимита → проходят
"""

from src.config.extraction_settings import ExtractionSettings


def _make_client(settings: ExtractionSettings = None):
    """Создаёт OllamaClient с mock-фабрикой для тестов фильтра."""
    from unittest.mock import MagicMock
    from src.infrastructure.llm.clients.ollama_client import OllamaClient

    factory = MagicMock()
    factory.create_json.return_value = MagicMock()
    return OllamaClient(factory, settings or ExtractionSettings())


class TestTooShort:

    def test_single_char_rejected(self):
        client = _make_client()
        assert client._is_bad_entity("а") is True

    def test_empty_string_rejected(self):
        client = _make_client()
        assert client._is_bad_entity("") is True


class TestTooLong:

    def test_over_max_chars_rejected(self):
        client = _make_client(ExtractionSettings(max_entity_name_chars=20))
        long_name = "А" * 21
        assert client._is_bad_entity(long_name) is True

    def test_at_max_chars_passes(self):
        client = _make_client(ExtractionSettings(max_entity_name_chars=20))
        name = "А" * 20
        assert client._is_bad_entity(name) is False

    def test_over_max_words_rejected(self):
        client = _make_client(ExtractionSettings(max_entity_name_words=3))
        assert client._is_bad_entity("один два три четыре") is True

    def test_at_max_words_passes(self):
        client = _make_client(ExtractionSettings(max_entity_name_words=3))
        assert client._is_bad_entity("Один Два Три") is False


class TestSingleLowercaseWord:
    """Одно нарицательное строчное слово = скорее всего не сущность."""

    def test_lowercase_single_word_rejected(self):
        client = _make_client()
        assert client._is_bad_entity("модель") is True

    def test_another_lowercase_word_rejected(self):
        client = _make_client()
        assert client._is_bad_entity("система") is True

    def test_any_language_lowercase_rejected(self):
        client = _make_client()
        assert client._is_bad_entity("process") is True

    def test_lowercase_with_digits_passes(self):
        """'gpt4' содержит цифру → не чисто alpha → проходит."""
        client = _make_client()
        assert client._is_bad_entity("gpt4") is False

    def test_lowercase_with_hyphen_passes(self):
        """'self-attention' — не isalpha() → проходит."""
        client = _make_client()
        assert client._is_bad_entity("self-attention") is False


class TestProperNames:
    """Имена собственные, аббревиатуры, технологии — проходят."""

    def test_capitalized_single_word_passes(self):
        client = _make_client()
        assert client._is_bad_entity("Колобок") is False

    def test_uppercase_abbreviation_passes(self):
        client = _make_client()
        assert client._is_bad_entity("BERT") is False
        assert client._is_bad_entity("GPT") is False
        assert client._is_bad_entity("NLP") is False

    def test_mixed_case_tech_passes(self):
        client = _make_client()
        assert client._is_bad_entity("AlexNet") is False
        assert client._is_bad_entity("BioBERT") is False

    def test_product_with_version_passes(self):
        client = _make_client()
        assert client._is_bad_entity("GPT-4") is False
        assert client._is_bad_entity("Llama 2") is False

    def test_organization_name_passes(self):
        client = _make_client()
        assert client._is_bad_entity("OpenAI") is False
        assert client._is_bad_entity("Stanford NLP") is False
        assert client._is_bad_entity("Google AI") is False

    def test_person_name_passes(self):
        client = _make_client()
        assert client._is_bad_entity("Джеффри Хинтон") is False

    def test_date_passes(self):
        client = _make_client()
        assert client._is_bad_entity("2020 год") is False
        assert client._is_bad_entity("2022-2023 годы") is False


class TestConfigurableLimits:
    """Лимиты берутся из ExtractionSettings."""

    def test_custom_min_chars(self):
        client = _make_client(ExtractionSettings(min_entity_name_chars=5))
        assert client._is_bad_entity("BERT") is True  # 4 < 5
        assert client._is_bad_entity("BLOOM") is False  # 5 == 5

    def test_custom_max_words(self):
        client = _make_client(ExtractionSettings(max_entity_name_words=2))
        assert client._is_bad_entity("Stanford NLP") is False  # 2
        assert client._is_bad_entity("Google AI Lab") is True  # 3