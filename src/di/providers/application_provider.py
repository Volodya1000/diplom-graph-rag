from dishka import Provider, Scope, provide

from src.application.use_cases.export_ontology import ExportOntologyUseCase
from src.application.use_cases.update_ontology_use_case import UpdateOntologyUseCase
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.resolution_rules import EntityResolutionMatcher
from src.application.services.entity_resolution_service import (
    EntityResolutionOrchestrator,
)
from src.application.services.post_processing_service import PostProcessingService
from src.application.use_cases.ingest_document import IngestDocumentUseCase
from src.application.use_cases.seed_tbox import SeedTboxUseCase


class ApplicationProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_matcher(self) -> EntityResolutionMatcher:
        return EntityResolutionMatcher(levenshtein_threshold=0.85)

    er_orchestrator = provide(EntityResolutionOrchestrator, scope=Scope.APP)
    post_processor = provide(PostProcessingService, scope=Scope.APP)
    ingest_use_case = provide(IngestDocumentUseCase, scope=Scope.APP)
    seed_tbox_use_case = provide(SeedTboxUseCase, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def provide_export_ontology_use_case(
            self,
            schema_repo: ISchemaRepository,
    ) -> ExportOntologyUseCase:
        return ExportOntologyUseCase(schema_repo)

    @provide(scope=Scope.APP)
    def provide_update_ontology_use_case(
        self, schema_repo: ISchemaRepository
    ) -> UpdateOntologyUseCase:
        return UpdateOntologyUseCase(schema_repo)