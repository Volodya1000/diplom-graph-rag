import logging
import time
from src.application.use_cases.ingest_pipeline.context import IIngestStep, IngestContext
from src.domain.aggregates.instance_aggregate import InstanceAggregate
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
        registry = self.er_svc.create_registry()
        t_pipeline = time.monotonic()

        for idx, chunk in enumerate(ctx.domain_chunks, 1):
            t_chunk = time.monotonic()

            current_classes = await self.schema_repo.get_tbox_classes()
            current_relations = await self.schema_repo.get_schema_relations()

            extraction = await self.llm.extract_entities_and_triples(
                text=chunk.text,
                tbox_classes=current_classes,
                tbox_relations=current_relations,
                known_entities=registry.format_known_entities(),
            )

            if not extraction.entities and not extraction.triples:
                logger.info(
                    f"  [{idx}/{ctx.total_chunks}] Чанк {chunk.chunk_index}: "
                    f"пусто ({time.monotonic() - t_chunk:.1f}s)"
                )
                continue

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

            if new_classes:
                await self.schema_repo.save_tbox_classes(new_classes)
            if new_relations:
                await self.schema_repo.save_schema_relations(new_relations)

            for inst in instances:
                if inst.instance_id not in ctx.saved_instance_ids:
                    await self.instance_repo.save_instance(inst)
                    inst_agg = InstanceAggregate(instance=inst)
                    await self.edge_repo.save_edges(inst_agg.build_edges())
                    ctx.saved_instance_ids.add(inst.instance_id)

            for triple in resolved_triples:
                await self.instance_repo.save_instance_relation(triple)

            ctx.total_entities += len(instances)
            ctx.total_triples += len(resolved_triples)

            logger.info(
                f"  [{idx}/{ctx.total_chunks}] Чанк {chunk.chunk_index}: "
                f"+{len(instances)} entities, +{len(resolved_triples)} triples "
                f"({time.monotonic() - t_chunk:.1f}s)"
            )

        logger.info(
            f"📊 Pipeline done: {ctx.total_entities} entities, "
            f"{ctx.total_triples} triples, "
            f"{len(ctx.saved_instance_ids)} unique nodes "
            f"({time.monotonic() - t_pipeline:.1f}s)"
        )
