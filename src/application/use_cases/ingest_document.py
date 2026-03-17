"""
Use Case: Полная индексация PDF → граф знаний.

Зависимости разделены по ISP — каждый репозиторий отвечает
за свою область ответственности.
"""

import logging
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
    ):
        self.parser = parser
        self.schema_repo = schema_repo
        self.doc_repo = doc_repo
        self.instance_repo = instance_repo
        self.edge_repo = edge_repo
        self.embedder = embedder
        self.llm = llm
        self.er_svc = er_svc

    # ------------------------------------------------------------------

    async def _ensure_tbox(self) -> None:
        await self.schema_repo.ensure_indexes()

        current_classes = await self.schema_repo.get_tbox_classes()
        current_relations = await self.schema_repo.get_schema_relations()

        if current_classes:
            logger.info(
                f"📚 T-Box: {len(current_classes)} классов, "
                f"{len(current_relations)} отношений"
            )
            return

        logger.warning("⚠️ T-Box пуст — автоинициализация…")
        from src.domain.ontology.base_tbox import (
            BASE_TBOX_CLASSES, BASE_TBOX_RELATIONS,
        )
        await self.schema_repo.save_tbox_classes(BASE_TBOX_CLASSES)
        await self.schema_repo.save_schema_relations(BASE_TBOX_RELATIONS)
        logger.info("📚 T-Box создан")

    # ------------------------------------------------------------------

    async def execute(self, file_path: Path) -> str:
        logger.info(f"📄 Start ingest: {file_path}")
        await self._ensure_tbox()

        doc = DocumentNode(filename=file_path.name)

        # === PARSE ===
        dl_doc = self.parser.parse_pdf(str(file_path))
        logger.info("📥 PDF parsed")

        processed_chunks = self.parser.chunk_document(dl_doc)
        logger.info(f"✂️ Chunks: {len(processed_chunks)}")

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
        embeddings = await self.embedder.embed_texts_batch(
            [c.text for c in domain_chunks],
        )
        for i, chunk in enumerate(domain_chunks):
            chunk.embedding = embeddings[i]
        logger.info(f"🧠 Embeddings: {len(embeddings)}")

        # === SAVE DOC + CHUNKS ===
        await self.doc_repo.save_document(doc)
        for chunk in domain_chunks:
            await self.doc_repo.save_chunk(chunk)

        doc_agg = DocumentAggregate(document=doc, chunks=domain_chunks)
        await self.edge_repo.save_edges(doc_agg.build_edges())
        logger.info(f"💾 Документ + {len(domain_chunks)} чанков сохранены")

        # === ENTITY + TRIPLE PIPELINE ===
        registry = self.er_svc.create_registry()

        total_entities = 0
        total_triples = 0
        saved_instance_ids: set = set()

        for chunk in domain_chunks:
            logger.info(
                f"🔍 Чанк {chunk.chunk_index} "
                f"({len(chunk.text)} символов)"
            )

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
            logger.info(
                f"🤖 Извлечено: {len(extraction.entities)} сущностей, "
                f"{len(extraction.triples)} троек"
            )

            if not extraction.entities and not extraction.triples:
                continue

            (
                instances, new_classes, resolved_triples, new_relations,
            ) = await self.er_svc.process_extraction(
                extraction,
                current_classes,
                current_relations,
                chunk.chunk_id,
                registry,
            )

            logger.info(
                f"🧩 ER → instances={len(instances)}, "
                f"triples={len(resolved_triples)}, "
                f"new_classes={len(new_classes)}, "
                f"new_rels={len(new_relations)}"
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

        logger.info(
            f"✅ Ingest завершён: "
            f"entities={total_entities}, "
            f"triples={total_triples}, "
            f"unique={len(saved_instance_ids)}"
        )
        return doc.doc_id