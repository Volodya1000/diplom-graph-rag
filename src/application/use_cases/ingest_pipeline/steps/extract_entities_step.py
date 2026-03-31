import logging
import time
from tqdm import tqdm
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.domain.services.builders.edge_builder import GraphEdgeBuilder
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.application.services.entity_resolution_service import (
    EntityResolutionOrchestrator,
)

logger = logging.getLogger(__name__)


class ExtractEntitiesAndTriplesStep(IIngestStep):
    def __init__(
        self,
        llm: ILLMClient,
        schema_repo: ISchemaRepository,
        instance_repo: IInstanceRepository,
        edge_repo: IEdgeRepository,
        er_svc: EntityResolutionOrchestrator,
    ):
        self.llm = llm
        self.schema_repo = schema_repo
        self.instance_repo = instance_repo
        self.edge_repo = edge_repo
        self.er_svc = er_svc

    async def execute(self, ctx: IngestContext) -> None:
        if not ctx.domain_chunks:
            logger.warning("⚠️ Нет чанков для извлечения сущностей")
            return

        registry = self.er_svc.create_registry()
        total_chunks = len(ctx.domain_chunks)

        logger.info(
            f"🔍 Запуск извлечения сущностей и триплетов из {total_chunks} чанков"
        )

        for idx, chunk in enumerate(
            tqdm(ctx.domain_chunks, desc="📝 Извлечение сущностей", unit="chunk"), 1
        ):
            start_time = time.monotonic()

            current_classes = await self.schema_repo.get_tbox_classes()
            current_relations = await self.schema_repo.get_schema_relations()

            # ==================== LLM ВЫЗОВ ====================
            extraction = await self.llm.extract_entities_and_triples(
                text=chunk.text,
                tbox_classes=current_classes,
                tbox_relations=current_relations,
                known_entities=registry.format_known_entities(),
            )

            duration = time.monotonic() - start_time

            # ==================== ДЕТАЛЬНЫЙ ЛОГ ПО ЧАНКУ ====================
            logger.info(
                f"✅ Чанк {idx:2d}/{total_chunks} | "
                f"сущностей: {len(extraction.entities):2d} | "
                f"триплетов: {len(extraction.triples):2d} | "
                f"время: {duration:.1f}с"
            )

            # Показываем конкретные сущности
            if extraction.entities:
                entities_str = ", ".join(
                    f"{e.name} [{e.type}]" for e in extraction.entities
                )
                logger.info(f"   📌 Сущности: {entities_str}")
            else:
                logger.info("   📌 Сущности: (нет)")

            # Показываем конкретные триплеты
            if extraction.triples:
                for t in extraction.triples:
                    logger.info(f"   🔗 {t.subject} → {t.predicate} → {t.object}")
            else:
                logger.info("   🔗 Триплеты: (нет)")

            # ==================== ОБРАБОТКА И СОХРАНЕНИЕ ====================
            (
                instances,
                new_classes,
                resolved_triples,
                new_relations,
            ) = await self.er_svc.process_extraction(
                extraction,
                current_classes,
                current_relations,
                chunk.chunk_id,
                registry,
            )

            # Новые классы
            if new_classes:
                logger.info(f"   ➕ Добавлено новых классов: {len(new_classes)}")
                for c in new_classes:
                    logger.info(f"      → {c.name} (draft)")

            # Новые отношения
            if new_relations:
                logger.info(f"   ➕ Добавлено новых отношений: {len(new_relations)}")
                for r in new_relations:
                    logger.info(
                        f"      → {r.source_class} --{r.relation_name}→ {r.target_class}"
                    )

            # Сохранение экземпляров
            saved_this_chunk = 0
            for inst in instances:
                if inst.instance_id not in ctx.saved_instance_ids:
                    await self.instance_repo.save_instance(inst)
                    edges = GraphEdgeBuilder.build_instance_edges(instance=inst)
                    await self.edge_repo.save_edges(edges)
                    ctx.saved_instance_ids.add(inst.instance_id)
                    saved_this_chunk += 1

            # Сохранение триплетов
            for triple in resolved_triples:
                await self.instance_repo.save_instance_relation(triple)

            ctx.total_entities += len(instances)
            ctx.total_triples += len(resolved_triples)

            logger.debug(
                f"   Сохранено в этом чанке: {saved_this_chunk} новых сущностей"
            )

        # ==================== ИТОГОВАЯ СВОДКА ====================
        logger.info(
            f"🎉 Извлечение сущностей завершено!\n"
            f"   Всего обработано чанков: {total_chunks}\n"
            f"   🧩 Сущностей сохранено: {ctx.total_entities}\n"
            f"   🔗 Триплетов сохранено: {ctx.total_triples}"
        )
