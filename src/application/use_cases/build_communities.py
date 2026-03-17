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
        min_community_size: int = 2,
        generate_summaries: bool = True,
        force: bool = False,
    ) -> dict:
        logger.info(
            f"🧩 Build communities: "
            f"algorithm={algorithm}, force={force}"
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

        # 3. Генерация summaries
        communities = await self._analytics.get_communities()
        summaries_count = 0

        for comm in communities:
            if comm.entity_count < min_community_size:
                continue
            if comm.summary and not force:
                continue

            members = await self._analytics.get_community_members(
                comm.community_id,
            )
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

    @staticmethod
    def _build_context(
        community_id: int,
        members: list[dict],
    ) -> str:
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

        return COMMUNITY_CONTEXT_TEMPLATE.format(
            community_id=community_id,
            members_text=members_text,
            relations_text=relations_text,
        )