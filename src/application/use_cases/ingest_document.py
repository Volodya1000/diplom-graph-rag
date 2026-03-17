from pathlib import Path
from src.domain.models import DocumentNode, ChunkNode, DocumentAggregate
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.llm.llm_client import ILLMClient
from src.infrastructure.docling.doc_processor import DocProcessor
from src.application.services.entity_resolution_service import EntityResolutionOrchestrator


class IngestDocumentUseCase:
    def __init__(
            self,
            parser: DocProcessor,
            repo: IGraphRepository,
            embedder: IEmbeddingService,
            llm: ILLMClient,
            er_svc: EntityResolutionOrchestrator
    ):
        self.parser = parser
        self.repo = repo
        self.embedder = embedder
        self.llm = llm
        self.er_svc = er_svc

    async def execute(self, file_path: Path) -> str:
        # 1. Domain Object
        doc = DocumentNode(filename=file_path.name)

        # 2. Parse (Infrastructure)
        dl_doc = self.parser.parse_pdf(str(file_path))
        processed_chunks = self.parser.chunk_document(dl_doc)

        # 3. Map Infrastructure DTO to Domain Entity
        domain_chunks = [
            ChunkNode(
                doc_id=doc.doc_id,
                chunk_index=c.metadata.chunk_index,
                text=c.enriched_text,
                headings=c.metadata.headings,
                start_page=c.metadata.start_page,
                end_page=c.metadata.end_page
            ) for c in processed_chunks
        ]

        # 4. Batch Embedding
        chunk_texts = [c.text for c in domain_chunks]
        embeddings = await self.embedder.embed_texts_batch(chunk_texts)
        for i, chunk in enumerate(domain_chunks):
            chunk.embedding = embeddings[i]

        # 5. Сохраняем через примитивные методы (логика рёбер — в домене!)
        await self.repo.save_document(doc)
        for chunk in domain_chunks:
            await self.repo.save_chunk(chunk)

        # 6. Строим граф в домене и сохраняем рёбра
        aggregate = DocumentAggregate(document=doc, chunks=domain_chunks)
        edges = aggregate.build_edges()
        await self.repo.save_edges(edges)

        # 7. Graph Extraction (остальная логика без изменений)
        for chunk in domain_chunks:
            current_tbox = await self.repo.get_tbox_classes()
            raw_entities = await self.llm.extract_entities(chunk.text, current_tbox)
            instances, new_classes = await self.er_svc.process_entities(raw_entities, current_tbox, chunk.chunk_id)
            await self.repo.save_tbox_classes(new_classes)
            await self.repo.save_instances(instances)

        return doc.doc_id