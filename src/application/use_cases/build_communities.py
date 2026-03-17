"""
Use Case: Community Detection + генерация summaries.

Шаги:
  1. Создать/обновить GDS-проекцию
  2. Запустить community detection (Leiden/Louvain)
  3. Для каждого сообщества — сгенерировать summary через LLM
  4. Сохранить summaries в граф
"""

import logging
from typing import Optional

from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.persistence.neo4j.session_manager import Neo4jSessionManager

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """\
На основе списка сущностей и их связей в сообществе графа знаний, \
напиши краткую сводку (2-4 предложения) о том, что объединяет \
эти сущности. Что это за тема/область/сюжет?

Отвечай на русском. Только сводка, без вступлений."""

_COMMUNITY_CONTEXT = """\
=== СУЩНОСТИ СООБЩЕСТВА #{community_id} ===
{members_text}

=== СВЯЗИ ===
{relations_text}"""


class BuildCommunitiesUseCase:
    def __init__(
        self,
        analytics: IGraphAnalyticsService,
        generator: IAnswerGenerator,
        session_manager: Neo4jSessionManager,
    ):
        self._analytics = analytics
        self._generator = generator
        self._sm = session_manager

    async def execute(
        self,
        algorithm: str = "leiden",
        min_community_size: int = 2,
        generate_summaries: bool = True,
        force: bool = False,
    ) -> dict:
        """
        Args:
            algorithm: 'leiden' или 'louvain'
            min_community_size: мин. размер для генерации summary
            generate_summaries: генерировать ли summaries через LLM
            force: пересоздать проекцию и пересчитать

        Returns:
            {"communities": N, "summaries_generated": M}
        """
        logger.info(
            f"🧩 Build communities: algorithm={algorithm}, "
            f"force={force}"
        )

        # 1. Проекция
        if force:
            await self._analytics.drop_projection()
        await self._analytics.ensure_projection()

        # 2. Community detection
        community_count = await self._analytics.detect_communities(
            algorithm=algorithm,
        )
        logger.info(f"🧩 Найдено сообществ: {community_count}")

        if not generate_summaries:
            return {
                "communities": community_count,
                "summaries_generated": 0,
            }

        # 3. Получаем сообщества
        communities = await self._analytics.get_communities()
        summaries_count = 0

        for comm in communities:
            if comm.entity_count < min_community_size:
                continue

            # Пропускаем если summary уже есть и не force
            if comm.summary and not force:
                continue

            # 4. Получаем участников с связями
            members = await self._analytics.get_community_members(
                comm.community_id,
            )

            if not members:
                continue

            # Формируем контекст для LLM
            members_text = "\n".join(
                f"• {m['name']} [{m['class_name']}]"
                for m in members
            )

            relations_lines = []
            for m in members:
                for rel in m.get("relations", []):
                    if rel.get("target"):
                        relations_lines.append(
                            f"  {m['name']} —{rel['predicate']}→ "
                            f"{rel['target']}"
                        )
            relations_text = (
                "\n".join(relations_lines)
                if relations_lines
                else "(нет связей)"
            )

            context = _COMMUNITY_CONTEXT.format(
                community_id=comm.community_id,
                members_text=members_text,
                relations_text=relations_text,
            )

            # 5. Генерируем summary
            summary = await self._generator.generate(
                question="Кратко опиши это сообщество",
                context=context,
                system_prompt=_SUMMARY_PROMPT,
            )

            # 6. Сохраняем
            await self._save_summary(
                comm.community_id, summary, comm.key_entities,
            )
            summaries_count += 1

            logger.info(
                f"📝 Community #{comm.community_id} "
                f"({comm.entity_count} entities): "
                f"{summary[:80]}…"
            )

        result = {
            "communities": community_count,
            "summaries_generated": summaries_count,
        }
        logger.info(f"✅ Build communities done: {result}")
        return result

    async def _save_summary(
        self,
        community_id: int,
        summary: str,
        key_entities: list[str],
    ) -> None:
        """Сохраняет summary как ноду CommunitySummary."""
        async with self._sm.session() as s:
            await s.run("""
                MERGE (cs:CommunitySummary {community_id: $cid})
                SET cs.summary       = $summary,
                    cs.key_entities   = $key_entities,
                    cs.updated_at     = datetime()
            """, {
                "cid": community_id,
                "summary": summary,
                "key_entities": key_entities[:20],
            })