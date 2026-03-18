"""
Unit: постфильтрация сущностей — структурные правила.
"""

from typing import Optional
from src.config.extraction_settings import ExtractionSettings


def _make_client(settings: Optional[ExtractionSettings] = None):
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
        assert client._is_bad_entity("А" * 21) is True

    def test_at_max_chars_passes(self):
        client = _make_client(ExtractionSettings(max_entity_name_chars=20))
        assert client._is_bad_entity("А" * 20) is False

    def test_over_max_words_rejected(self):
        client = _make_client(ExtractionSettings(max_entity_name_words=3))
        assert client._is_bad_entity("один два три четыре") is True

    def test_at_max_words_passes(self):
        client = _make_client(ExtractionSettings(max_entity_name_words=3))
        assert client._is_bad_entity("Один Два Три") is False


class TestSingleLowercaseWord:

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
        client = _make_client()
        assert client._is_bad_entity("gpt4") is False

    def test_lowercase_with_hyphen_passes(self):
        client = _make_client()
        assert client._is_bad_entity("self-attention") is False


class TestProperNames:

    def test_capitalized_single_word_passes(self):
        client = _make_client()
        assert client._is_bad_entity("Колобок") is False

    def test_uppercase_abbreviation_passes(self):
        client = _make_client()
        assert client._is_bad_entity("BERT") is False
        assert client._is_bad_entity("GPT") is False

    def test_mixed_case_tech_passes(self):
        client = _make_client()
        assert client._is_bad_entity("AlexNet") is False

    def test_product_with_version_passes(self):
        client = _make_client()
        assert client._is_bad_entity("GPT-4") is False
        assert client._is_bad_entity("Llama 2") is False

    def test_organization_name_passes(self):
        client = _make_client()
        assert client._is_bad_entity("OpenAI") is False
        assert client._is_bad_entity("Stanford NLP") is False

    def test_date_passes(self):
        client = _make_client()
        assert client._is_bad_entity("2020 год") is False


class TestConfigurableLimits:

    def test_custom_min_chars(self):
        client = _make_client(ExtractionSettings(min_entity_name_chars=5))
        assert client._is_bad_entity("BERT") is True
        assert client._is_bad_entity("BLOOM") is False

    def test_custom_max_words(self):
        client = _make_client(ExtractionSettings(max_entity_name_words=2))
        assert client._is_bad_entity("Stanford NLP") is False
        assert client._is_bad_entity("Google AI Lab") is True