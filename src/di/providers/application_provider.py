from dishka import Provider, Scope, provide
from src.domain.resolution_rules import EntityResolutionMatcher
from src.application.services.entity_resolution_service import EntityResolutionOrchestrator
from src.application.use_cases.ingest_document import IngestDocumentUseCase

class ApplicationProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_matcher(self) -> EntityResolutionMatcher:
        return EntityResolutionMatcher(levenshtein_threshold=0.85)

    er_orchestrator = provide(EntityResolutionOrchestrator, scope=Scope.APP)
    ingest_use_case = provide(IngestDocumentUseCase, scope=Scope.APP)