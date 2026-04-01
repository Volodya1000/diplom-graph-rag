"""
Use Case: Community Detection + генерация summaries.

Рефакторинг:
  - Убрана зависимость от Neo4jSessionManager (DIP)
  - Промпты вынесены в отдельный файл (SRP)
  - save_community_summary перенесён в IGraphAnalyticsService
"""

import logging

from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.infrastructure.llm.prompts.community_summary import (
    COMMUNITY_SUMMARY_SYSTEM,
    COMMUNITY_CONTEXT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class BuildCommunitiesUseCase:
    def __init__(
        self,
        analytics: IGraphAnalyticsService,
        generator: IAnswerGenerator,
    ):
        self._analytics = analytics
        self._generator = generator

    async def execute(
        self,
        algorithm: str = "leiden",
        min_community_size: int = 3,
        generate_summaries: bool = True,
        force: bool = False,
    ) -> dict:
        logger.info(
            f"🧩 Build communities: "
            f"algorithm={algorithm}, force={force}, min_size={min_community_size}"
        )

        # 1. Проекция
        if force:
            await self._analytics.drop_projection()
        await self._analytics.ensure_projection()

        # 2. Community detection (Сырой прогон)
        raw_count = await self._analytics.detect_communities(algorithm=algorithm)

        # 3. ЖЕСТКАЯ ОЧИСТКА: удаляем мелкий мусор
        await self._analytics.cleanup_small_communities(min_size=min_community_size)

        # 4. Получаем ИТОГОВЫЙ список валидных сообществ
        communities = await self._analytics.get_communities()
        valid_count = len(communities)
        logger.info(
            f"🧩 Итоговых валидных сообществ: {valid_count} (было до очистки: {raw_count})"
        )

        if not generate_summaries:
            return {
                "communities": valid_count,
                "summaries_generated": 0,
            }

        # 5. Генерация summaries (теперь eligible - это все оставшиеся)
        summaries_count = 0
        eligible = [c for c in communities if (force or not c.summary)]

        for i, comm in enumerate(eligible, 1):
            members = await self._analytics.get_community_members(comm.community_id)
            if not members:
                continue

            context = self._build_context(comm.community_id, members)

            summary = await self._generator.generate(
                question="Кратко опиши это сообщество",
                context=context,
                system_prompt=COMMUNITY_SUMMARY_SYSTEM,
            )

            await self._analytics.save_community_summary(
                community_id=comm.community_id,
                summary=summary,
                key_entities=comm.key_entities,
            )
            summaries_count += 1

            logger.info(
                f"📝 [{i}/{len(eligible)}] Community #{comm.community_id} "
                f"({comm.entity_count} entities): "
                f"{summary[:60]}…"
            )

        result = {
            "communities": valid_count,
            "summaries_generated": summaries_count,
        }
        logger.info(f"✅ Build communities done: {result}")
        return result

    @staticmethod
    def _build_context(
        community_id: int,
        members: list[dict],
    ) -> str:
        members_text = "\n".join(f"• {m['name']} [{m['class_name']}]" for m in members)

        relations_lines = []
        for m in members:
            for rel in m.get("relations", []):
                if rel.get("target"):
                    relations_lines.append(
                        f"  {m['name']} —{rel['predicate']}→ {rel['target']}"
                    )

        relations_text = (
            "\n".join(relations_lines) if relations_lines else "(нет связей)"
        )

        return COMMUNITY_CONTEXT_TEMPLATE.format(
            community_id=community_id,
            members_text=members_text,
            relations_text=relations_text,
        )
