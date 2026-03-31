from dishka import Provider, Scope, provide

from src.application.use_cases.export_ontology import ExportOntologyUseCase
from src.application.use_cases.update_ontology_use_case import UpdateOntologyUseCase
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.interfaces.llm.llm_client import ILLMClient

from src.infrastructure.docling.doc_processor import DocProcessor
from src.domain.resolution_rules import EntityResolutionMatcher
from src.application.services.entity_resolution_service import (
    EntityResolutionOrchestrator,
)
from src.application.services.post_processing_service import PostProcessingService
from src.application.use_cases.seed_tbox import SeedTboxUseCase

# Импорты нового пайплайна
from src.application.use_cases.ingest_pipeline.context import IIngestStep
from src.application.use_cases.ingest_pipeline.steps.ensure_tbox_step import (
    EnsureTBoxStep,
)
from src.application.use_cases.ingest_pipeline.steps.parse_and_chunk_step import (
    ParseAndChunkStep,
)
from src.application.use_cases.ingest_pipeline.steps.embed_chunks_step import (
    EmbedChunksStep,
)
from src.application.use_cases.ingest_pipeline.steps.save_structure_step import (
    SaveDocumentStructureStep,
)
from src.application.use_cases.ingest_pipeline.steps.extract_entities_step import (
    ExtractEntitiesAndTriplesStep,
)
from src.application.use_cases.ingest_pipeline.steps.post_process_step import (
    PostProcessSynonymsStep,
)
from src.application.use_cases.ingest_document import IngestDocumentUseCase


class ApplicationProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_matcher(self) -> EntityResolutionMatcher:
        return EntityResolutionMatcher(levenshtein_threshold=0.85)

    er_orchestrator = provide(EntityResolutionOrchestrator, scope=Scope.APP)
    post_processor = provide(PostProcessingService, scope=Scope.APP)
    seed_tbox_use_case = provide(SeedTboxUseCase, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def provide_ingest_use_case(
        self,
        schema_repo: ISchemaRepository,
        parser: DocProcessor,
        embedder: IEmbeddingService,
        doc_repo: IDocumentRepository,
        edge_repo: IEdgeRepository,
        llm: ILLMClient,
        instance_repo: IInstanceRepository,
        er_svc: EntityResolutionOrchestrator,
        post_processor: PostProcessingService,
    ) -> IngestDocumentUseCase:
        steps: list[IIngestStep] = [
            EnsureTBoxStep(schema_repo),
            ParseAndChunkStep(parser),
            EmbedChunksStep(embedder),
            SaveDocumentStructureStep(doc_repo, edge_repo),
            ExtractEntitiesAndTriplesStep(
                llm, schema_repo, instance_repo, edge_repo, er_svc
            ),
            PostProcessSynonymsStep(post_processor),
        ]
        return IngestDocumentUseCase(steps=steps)

    @provide(scope=Scope.APP)
    def provide_export_ontology_use_case(
        self, schema_repo: ISchemaRepository
    ) -> ExportOntologyUseCase:
        return ExportOntologyUseCase(schema_repo)

    @provide(scope=Scope.APP)
    def provide_update_ontology_use_case(
        self, schema_repo: ISchemaRepository
    ) -> UpdateOntologyUseCase:
        return UpdateOntologyUseCase(schema_repo)
