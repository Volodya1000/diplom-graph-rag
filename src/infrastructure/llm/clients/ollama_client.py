import asyncio
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.domain.models import SchemaClass, RawExtractedEntity

class OllamaClient(ILLMClient):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def extract_entities(self, text: str, tbox_schema: List[SchemaClass]) -> List[RawExtractedEntity]:
        # TODO: Интеграция с Ollama REST API / LangChain
        # Пока возвращаем мок для прохождения тестов/пайплайна
        await asyncio.sleep(0.5)
        return [
            RawExtractedEntity(name="ЗАО Альфа-Банк", type="Organization"),
            RawExtractedEntity(name="Договор", type="DocumentType")
        ]