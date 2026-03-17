"""
LLM-based synonym resolution.

Получает список сущностей → находит группы синонимов.
"""

import json
import re
import logging
from typing import List

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

from src.domain.interfaces.services.synonym_resolver import ISynonymResolver
from src.domain.graph_components.nodes import InstanceNode
from src.domain.value_objects.synonym_group import (
    SynonymGroup,
    SynonymResolutionResult,
)
from src.config.ollama_settings import OllamaSettings

logger = logging.getLogger(__name__)

_RE_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_RE_CODE_BLOCK = re.compile(r"```(?:json)?\s*", re.IGNORECASE)

_SYSTEM_PROMPT = """\
Ты — лингвистический анализатор. Твоя задача — найти сущности, \
которые являются СИНОНИМАМИ (обозначают одно и то же лицо, \
предмет или понятие, но названы по-разному).

ПРАВИЛА:
1. Группируй ТОЛЬКО очевидные синонимы.
2. Для каждой группы выбери КАНОНИЧЕСКОЕ имя (самое частое или \
   информативное).
3. Не группируй разные сущности! "Лиса" и "Волк" — разные персонажи.
4. Учитывай тип сущности — синонимы обычно одного типа.
5. Примеры синонимов: Старик/Дед, Старуха/Бабка, \
   Российская Федерация/Россия, СберБанк/Сбер.

Отвечай ТОЛЬКО валидным JSON. Без комментариев."""

_HUMAN_PROMPT = """\
=== КОНТЕКСТ ДОКУМЕНТА ===
{document_context}

=== СУЩНОСТИ ===
{entities_list}

=== ФОРМАТ ОТВЕТА ===
{{
  "groups": [
    {{
      "canonical_name": "Каноническое имя",
      "canonical_type": "Тип",
      "aliases": ["Синоним1", "Синоним2"],
      "reason": "Почему это синонимы"
    }}
  ]
}}

Если синонимов нет — верни {{"groups": []}}."""


class OllamaSynonymResolver(ISynonymResolver):
    def __init__(self, settings: OllamaSettings):
        self._llm = ChatOllama(
            model=settings.model_name,
            base_url=settings.base_url,
            temperature=0.1,
            num_ctx=settings.num_ctx,
            client_kwargs={"headers": settings.headers},
            format="json",
        )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", _HUMAN_PROMPT),
        ])

    async def find_synonym_groups(
        self,
        instances: List[InstanceNode],
        document_context: str,
    ) -> SynonymResolutionResult:
        if len(instances) < 2:
            return SynonymResolutionResult()

        # Дедупликация для промпта
        seen = set()
        entity_lines = []
        id_by_name: dict[str, list[str]] = {}

        for inst in instances:
            key = (inst.name.lower(), inst.class_name.lower())
            if key not in seen:
                seen.add(key)
                entity_lines.append(
                    f"• {inst.name} [{inst.class_name}]"
                )
            id_by_name.setdefault(inst.name.lower(), []).append(
                inst.instance_id,
            )

        entities_str = "\n".join(entity_lines)
        logger.info(
            f"🔍 Synonym analysis: {len(entity_lines)} unique entities"
        )

        try:
            chain = self._prompt | self._llm
            result: AIMessage = await chain.ainvoke({
                "document_context": document_context,
                "entities_list": entities_str,
            })

            text = result.content
            text = _RE_THINK.sub("", text)
            text = _RE_CODE_BLOCK.sub("", text).strip()

            parsed = json.loads(text)
            groups: list[SynonymGroup] = []

            for g in parsed.get("groups", []):
                canonical = g.get("canonical_name", "").strip()
                if not canonical:
                    continue

                aliases = [
                    a.strip() for a in g.get("aliases", []) if a.strip()
                ]
                if not aliases:
                    continue

                # Собираем instance_ids
                all_ids = set()
                for name_variant in [canonical] + aliases:
                    for iid in id_by_name.get(name_variant.lower(), []):
                        all_ids.add(iid)

                groups.append(SynonymGroup(
                    canonical_name=canonical,
                    canonical_type=g.get("canonical_type", ""),
                    aliases=aliases,
                    instance_ids=list(all_ids),
                    reason=g.get("reason", ""),
                ))

            merged = sum(len(g.aliases) for g in groups)
            logger.info(
                f"🔗 Synonym groups: {len(groups)}, "
                f"to merge: {merged} entities"
            )

            return SynonymResolutionResult(
                groups=groups,
                merged_count=merged,
                kept_count=len(entity_lines) - merged,
            )

        except Exception as e:
            logger.exception(f"❌ Synonym resolution failed: {e}")
            return SynonymResolutionResult()