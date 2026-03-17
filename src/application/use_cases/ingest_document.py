"""
Use Case: Полная индексация PDF-документа в граф знаний.
"""

import logging
from pathlib import Path

from src.domain.models import DocumentNode, ChunkNode, ExtractionResult
from src.domain.agregates.instance_agregate import InstanceAggregate
from src.domain.agregates.document_agregate import DocumentAggregate
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.infrastructure.docling.doc_processor import DocProcessor
from src.application.services.entity_resolution_service import (
    EntityResolutionOrchestrator,
)

logger = logging.getLogger(__name__)


class IngestDocumentUseCase:
    def __init__(
        self,
        parser: DocProcessor,
        repo: IGraphRepository,
        embedder: IEmbeddingService,
        llm: ILLMClient,
        er_svc: EntityResolutionOrchestrator,
    ):
        self.parser = parser
        self.repo = repo
        self.embedder = embedder
        self.llm = llm
        self.er_svc = er_svc

    # ------------------------------------------------------------------
    async def _ensure_tbox(self) -> None:
        """Проверяет T-Box; если пуст — автоматически засеивает."""
        current_classes = await self.repo.get_tbox_classes()
        current_relations = await self.repo.get_schema_relations()

        if current_classes:
            logger.info(
                f"📚 T-Box: {len(current_classes)} классов, "
                f"{len(current_relations)} отношений"
            )
            return

        logger.warning("⚠️ T-Box пуст! Автоматическая инициализация…")

        from src.domain.ontology.base_tbox import (
            BASE_TBOX_CLASSES, BASE_TBOX_RELATIONS,
        )

        await self.repo.save_tbox_classes(BASE_TBOX_CLASSES)
        await self.repo.save_schema_relations(BASE_TBOX_RELATIONS)

        logger.info(
            f"📚 Базовый T-Box создан: "
            f"{len(BASE_TBOX_CLASSES)} классов, "
            f"{len(BASE_TBOX_RELATIONS)} отношений"
        )

    # ------------------------------------------------------------------
    async def execute(self, file_path: Path) -> str:
        logger.info(f"📄 Start ingest: {file_path}")

        # === ENSURE T-BOX ===
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
        chunk_texts = [c.text for c in domain_chunks]
        embeddings = await self.embedder.embed_texts_batch(chunk_texts)
        logger.info(f"🧠 Embeddings: {len(embeddings)}")

        for i, chunk in enumerate(domain_chunks):
            chunk.embedding = embeddings[i]

        # === SAVE DOCUMENT + CHUNKS ===
        await self.repo.save_document(doc)
        logger.info("💾 Document saved")

        for chunk in domain_chunks:
            await self.repo.save_chunk(chunk)
        logger.info(f"💾 Chunks saved: {len(domain_chunks)}")

        doc_aggregate = DocumentAggregate(document=doc, chunks=domain_chunks)
        doc_edges = doc_aggregate.build_edges()
        await self.repo.save_edges(doc_edges)
        logger.info(f"🔗 Document edges: {len(doc_edges)}")

        # === ENTITY + TRIPLE EXTRACTION ===
        total_entities = 0
        total_triples = 0

        for chunk in domain_chunks:
            logger.info(
                f"🔍 Chunk {chunk.chunk_index} ({len(chunk.text)} chars)"
            )

            # Актуальный T-Box (растёт от чанка к чанку)
            current_classes = await self.repo.get_tbox_classes()
            current_relations = await self.repo.get_schema_relations()

            # --- LLM: извлечение сущностей + троек ---
            extraction: ExtractionResult = (
                await self.llm.extract_entities_and_triples(
                    chunk.text, current_classes, current_relations,
                )
            )
            logger.info(
                f"🤖 Extracted: {len(extraction.entities)} entities, "
                f"{len(extraction.triples)} triples"
            )

            if not extraction.entities and not extraction.triples:
                continue

            # --- Entity Resolution + валидация троек ---
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
            )

            logger.info(
                f"🧩 ER → instances={len(instances)}, "
                f"triples={len(resolved_triples)}, "
                f"new_classes={len(new_classes)}, "
                f"new_relations={len(new_relations)}"
            )

            # --- Сохранение новых элементов схемы ---
            if new_classes:
                await self.repo.save_tbox_classes(new_classes)
                logger.info(
                    f"📚 Новые классы: "
                    f"{[c.name for c in new_classes]}"
                )

            if new_relations:
                await self.repo.save_schema_relations(new_relations)
                logger.info(
                    f"📚 Новые отношения: "
                    + ", ".join(
                        f"{r.source_class}→{r.relation_name}→{r.target_class}"
                        for r in new_relations
                    )
                )

            # --- Сохранение экземпляров ---
            for inst in instances:
                await self.repo.save_instance(inst)
                inst_agg = InstanceAggregate(instance=inst)
                inst_edges = inst_agg.build_edges()
                await self.repo.save_edges(inst_edges)

            # --- Сохранение семантических связей ---
            for triple in resolved_triples:
                await self.repo.save_instance_relation(triple)

            total_entities += len(instances)
            total_triples += len(resolved_triples)

        logger.info(
            f"✅ Ingest finished: "
            f"entities={total_entities}, triples={total_triples}"
        )
        return doc.doc_id