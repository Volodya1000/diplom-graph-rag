import logging

from pydantic import BaseModel, Field

from src.domain.interfaces.services.answer_generator import IAnswerGenerator
from src.domain.interfaces.services.graph_analytics_service import (
    IGraphAnalyticsService,
)
from src.infrastructure.llm.prompts.community_summary import (
    COMMUNITY_CONTEXT_TEMPLATE,
    COMMUNITY_SUMMARY_SYSTEM,
)

logger = logging.getLogger(__name__)


class CommunitySummaryOutput(BaseModel):
    """Structured output для summary сообщества."""

    name: str = Field(description="Емкое название сообщества (3-6 слов)")

    summary: str = Field(description="Краткое описание сообщества (2-4 предложения)")


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
            "🧩 Build communities: algorithm=%s, force=%s, min_size=%s",
            algorithm,
            force,
            min_community_size,
        )

        if force:
            await self._analytics.drop_projection()

        await self._analytics.ensure_projection()

        raw_count = await self._analytics.detect_communities(algorithm=algorithm)

        await self._analytics.cleanup_small_communities(min_size=min_community_size)

        communities = await self._analytics.get_communities()

        valid_count = len(communities)

        logger.info(
            "🧩 Итоговых валидных сообществ: %s (было до очистки: %s)",
            valid_count,
            raw_count,
        )

        if not generate_summaries:
            return {
                "communities": valid_count,
                "summaries_generated": 0,
            }

        eligible = [c for c in communities if force or not c.summary]

        summaries_count = 0

        for index, community in enumerate(eligible, start=1):
            members = await self._analytics.get_community_members(community.community_id)

            if not members:
                continue

            context = self._build_context(
                community.community_id,
                members,
            )

            try:
                parsed = await self._generator.generate_structured(
                    question=("Проанализируй сообщество и создай краткое summary."),
                    context=context,
                    system_prompt=COMMUNITY_SUMMARY_SYSTEM,
                    output_model=CommunitySummaryOutput,
                )

                name = parsed.name.strip()
                summary = parsed.summary.strip()

            except Exception as e:
                logger.exception(
                    "❌ Community summary generation failed for %s: %s",
                    community.community_id,
                    e,
                )

                name = f"Сообщество #{community.community_id}"

                summary = "Не удалось автоматически сгенерировать описание сообщества."

            await self._analytics.save_community_summary(
                community_id=community.community_id,
                summary=summary,
                key_entities=community.key_entities,
                name=name,
            )

            summaries_count += 1

            logger.info(
                "📝[%s/%s] %s: %s…",
                index,
                len(eligible),
                name,
                summary,
            )

        result = {
            "communities": valid_count,
            "summaries_generated": summaries_count,
        }

        logger.info(
            "✅ Build communities done: %s",
            result,
        )

        return result

    @staticmethod
    def _build_context(
        community_id: int,
        members: list[dict],
    ) -> str:
        members_text = "\n".join(f"• {m['name']} [{m['class_name']}]" for m in members)

        relations_lines = [
            (f"  {m['name']} —{rel['predicate']}→ {rel['target']}")
            for m in members
            for rel in m.get("relations", [])
            if rel.get("target")
        ]

        relations_text = "\n".join(relations_lines) if relations_lines else "(нет связей)"

        return COMMUNITY_CONTEXT_TEMPLATE.format(
            community_id=community_id,
            members_text=members_text,
            relations_text=relations_text,
        )
