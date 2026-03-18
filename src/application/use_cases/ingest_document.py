"""
Use Case: Полная индексация PDF → граф знаний.

Улучшения логирования:
  - Прогресс чанков: chunk 5/66
  - Timing: общее и per-chunk
  - Итоговая сводка
"""

import logging
import time
from pathlib import Path

from src.domain.interfaces.llm.llm_client import ILLMClient, ExtractionResult
from src.domain.graph_components.nodes import DocumentNode, ChunkNode
from src.domain.agregates.instance_agregate import InstanceAggregate
from src.domain.agregates.document_agregate import DocumentAggregate
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.infrastructure.docling.doc_processor import DocProcessor
from src.application.services.entity_resolution_service import (
    EntityResolutionOrchestrator,
)
from src.application.services.post_processing_service import PostProcessingService

logger = logging.getLogger(__name__)


class IngestDocumentUseCase:
    def __init__(
        self,
        parser: DocProcessor,
        schema_repo: ISchemaRepository,
        doc_repo: IDocumentRepository,
        instance_repo: IInstanceRepository,
        edge_repo: IEdgeRepository,
        embedder: IEmbeddingService,
        llm: ILLMClient,
        er_svc: EntityResolutionOrchestrator,
        post_processor: PostProcessingService,
    ):
        self.parser = parser
        self.schema_repo = schema_repo
        self.doc_repo = doc_repo
        self.instance_repo = instance_repo
        self.edge_repo = edge_repo
        self.embedder = embedder
        self.llm = llm
        self.er_svc = er_svc
        self.post_processor = post_processor

    async def _ensure_tbox(self) -> None:
        await self.schema_repo.ensure_indexes()
        current_classes = await self.schema_repo.get_tbox_classes()
        if current_classes:
            return
        logger.warning("⚠️ T-Box пуст — автоинициализация…")
        from src.domain.ontology.base_tbox import (
            BASE_TBOX_CLASSES, BASE_TBOX_RELATIONS,
        )
        await self.schema_repo.save_tbox_classes(BASE_TBOX_CLASSES)
        await self.schema_repo.save_schema_relations(BASE_TBOX_RELATIONS)

    async def execute(
        self,
        file_path: Path,
        skip_synonyms: bool = False,
    ) -> str:
        t_start = time.monotonic()
        logger.info(f"📄 Start ingest: {file_path}")
        await self._ensure_tbox()

        doc = DocumentNode(filename=file_path.name)

        # === PARSE ===
        t_parse = time.monotonic()
        dl_doc = self.parser.parse_pdf(str(file_path))
        processed_chunks = self.parser.chunk_document(dl_doc)
        total_chunks = len(processed_chunks)
        logger.info(
            f"✂️ Parse + chunk: {total_chunks} chunks "
            f"({time.monotonic() - t_parse:.1f}s)"
        )

        domain_chunks = [
            ChunkNode(
                doc_id=doc.doc_id,
                chunk_index=c.metadata.chunk_index,
                text=c.enriched_text,
                headings=c.metadata.headings,
                start_page=c.metadata.start_page,
                end_page=c.metadata.end_page,
            )
            for c in processed_chunks
        ]

        # === EMBEDDINGS ===
        t_embed = time.monotonic()
        embeddings = await self.embedder.embed_texts_batch(
            [c.text for c in domain_chunks],
        )
        for i, chunk in enumerate(domain_chunks):
            chunk.embedding = embeddings[i]
        logger.info(
            f"🧠 Embeddings: {len(embeddings)} "
            f"({time.monotonic() - t_embed:.1f}s)"
        )

        # === SAVE DOC + CHUNKS ===
        await self.doc_repo.save_document(doc)
        for chunk in domain_chunks:
            await self.doc_repo.save_chunk(chunk)
        doc_agg = DocumentAggregate(document=doc, chunks=domain_chunks)
        await self.edge_repo.save_edges(doc_agg.build_edges())
        logger.info(f"💾 Документ + {total_chunks} чанков сохранены")

        # === ENTITY + TRIPLE PIPELINE ===
        registry = self.er_svc.create_registry()
        total_entities = total_triples = 0
        saved_instance_ids: set = set()
        t_pipeline = time.monotonic()

        for idx, chunk in enumerate(domain_chunks, 1):
            t_chunk = time.monotonic()

            current_classes = await self.schema_repo.get_tbox_classes()
            current_relations = await self.schema_repo.get_schema_relations()

            extraction: ExtractionResult = (
                await self.llm.extract_entities_and_triples(
                    text=chunk.text,
                    tbox_classes=current_classes,
                    tbox_relations=current_relations,
                    known_entities=registry.format_known_entities(),
                )
            )

            if not extraction.entities and not extraction.triples:
                logger.info(
                    f"  [{idx}/{total_chunks}] Чанк {chunk.chunk_index}: "
                    f"пусто ({time.monotonic() - t_chunk:.1f}s)"
                )
                continue

            (
                instances, new_classes, resolved_triples, new_relations,
            ) = await self.er_svc.process_extraction(
                extraction, current_classes, current_relations,
                chunk.chunk_id, registry,
            )

            if new_classes:
                await self.schema_repo.save_tbox_classes(new_classes)
            if new_relations:
                await self.schema_repo.save_schema_relations(new_relations)

            for inst in instances:
                if inst.instance_id not in saved_instance_ids:
                    await self.instance_repo.save_instance(inst)
                    inst_agg = InstanceAggregate(instance=inst)
                    await self.edge_repo.save_edges(inst_agg.build_edges())
                    saved_instance_ids.add(inst.instance_id)

            for triple in resolved_triples:
                await self.instance_repo.save_instance_relation(triple)

            total_entities += len(instances)
            total_triples += len(resolved_triples)

            chunk_time = time.monotonic() - t_chunk
            logger.info(
                f"  [{idx}/{total_chunks}] Чанк {chunk.chunk_index}: "
                f"+{len(instances)} entities, "
                f"+{len(resolved_triples)} triples "
                f"({chunk_time:.1f}s)"
            )

        pipeline_time = time.monotonic() - t_pipeline
        logger.info(
            f"📊 Pipeline done: {total_entities} entities, "
            f"{total_triples} triples, "
            f"{len(saved_instance_ids)} unique nodes "
            f"({pipeline_time:.1f}s)"
        )

        # === POST-PROCESSING ===
        if not skip_synonyms and total_entities > 1:
            t_syn = time.monotonic()
            logger.info("🔍 Post-processing: synonym resolution…")
            syn_result = await self.post_processor.resolve_synonyms(
                doc_id=doc.doc_id,
                document_context=f"Документ: {file_path.name}",
            )
            logger.info(
                f"🔗 Synonyms: merged={syn_result.merged_count}, "
                f"groups={len(syn_result.groups)} "
                f"({time.monotonic() - t_syn:.1f}s)"
            )

        total_time = time.monotonic() - t_start
        logger.info(
            f"✅ Ingest complete: doc_id={doc.doc_id}\n"
            f"   📄 File: {file_path.name}\n"
            f"   ✂️  Chunks: {total_chunks}\n"
            f"   🧩 Entities: {total_entities} (unique: {len(saved_instance_ids)})\n"
            f"   🔗 Triples: {total_triples}\n"
            f"   ⏱️  Total: {total_time:.1f}s "
            f"(avg {total_time / max(total_chunks, 1):.1f}s/chunk)"
        )
        return doc.doc_id