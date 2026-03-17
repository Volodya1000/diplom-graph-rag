import logging
from pathlib import Path

from src.domain.models import (
    DocumentNode, ChunkNode, DocumentAggregate, InstanceAggregate,
)
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.infrastructure.docling.doc_processor import DocProcessor
from src.application.services.entity_resolution_service import EntityResolutionOrchestrator

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
        """Проверяет T-Box; если пуст — автоматически засеивает базовые классы."""
        current = await self.repo.get_tbox_classes()
        if current:
            logger.info(f"📚 T-Box содержит {len(current)} классов")
            return

        logger.warning("⚠️ T-Box пуст! Автоматическая инициализация базовыми классами...")

        from src.domain.ontology.base_tbox import BASE_TBOX_CLASSES
        await self.repo.save_tbox_classes(BASE_TBOX_CLASSES)
        logger.info(
            f"📚 Базовый T-Box создан: "
            f"{', '.join(c.name for c in BASE_TBOX_CLASSES)}"
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
        logger.info(f"✂️ Chunks created: {len(processed_chunks)}")

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
        logger.info(f"🧠 Embeddings generated: {len(embeddings)}")

        for i, chunk in enumerate(domain_chunks):
            chunk.embedding = embeddings[i]

        # === SAVE DOC + CHUNKS ===
        await self.repo.save_document(doc)
        logger.info(f"💾 Document saved: {doc.doc_id}")

        for chunk in domain_chunks:
            await self.repo.save_chunk(chunk)
        logger.info(f"💾 Chunks saved: {len(domain_chunks)}")

        doc_aggregate = DocumentAggregate(document=doc, chunks=domain_chunks)
        edges = doc_aggregate.build_edges()
        await self.repo.save_edges(edges)
        logger.info(f"🔗 Document edges saved: {len(edges)}")

        # === ENTITY EXTRACTION PIPELINE ===
        total_entities = 0

        for chunk in domain_chunks:
            logger.info(f"🔍 Processing chunk {chunk.chunk_index}")

            # Актуальный T-Box (может расти от чанка к чанку)
            current_tbox = await self.repo.get_tbox_classes()
            logger.debug(f"TBOX classes: {[c.name for c in current_tbox]}")

            raw_entities = await self.llm.extract_entities(
                chunk.text, current_tbox
            )
            logger.info(f"🤖 Raw entities extracted: {len(raw_entities)}")

            instances, new_classes = await self.er_svc.process_entities(
                raw_entities, current_tbox, chunk.chunk_id
            )

            logger.info(
                f"🧩 ER result → instances: {len(instances)}, "
                f"new_classes: {len(new_classes)}"
            )

            if new_classes:
                await self.repo.save_tbox_classes(new_classes)
                logger.info(
                    f"📚 New TBOX classes saved: "
                    f"{[c.name for c in new_classes]}"
                )

            for inst in instances:
                await self.repo.save_instance(inst)
                inst_aggregate = InstanceAggregate(instance=inst)
                inst_edges = inst_aggregate.build_edges()
                await self.repo.save_edges(inst_edges)

            total_entities += len(instances)

        logger.info(
            f"✅ Ingest finished: doc_id={doc.doc_id}, "
            f"total_entities={total_entities}"
        )
        return doc.doc_id