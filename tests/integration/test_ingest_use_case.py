import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
from src.domain.ontology.schema import SchemaClass, SchemaStatus
from src.domain.models.extraction import (
    ExtractionResult,
    RawExtractedEntity,
    RawExtractedTriple,
)
from src.application.use_cases.ingest_document import IngestDocumentUseCase
from src.application.use_cases.ingest_pipeline.context import IIngestStep
from src.application.services.entity_resolution_service import (
    EntityResolutionOrchestrator,
)
from src.application.services.post_processing_service import PostProcessingService
from src.domain.resolution_rules import EntityResolutionMatcher
from src.domain.models.synonym import SynonymResolutionResult
from src.infrastructure.docling.dtos import ProcessedChunk, ChunkMetadata
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
from src.config.rag_settings import RAGSettings

pytestmark = pytest.mark.integration


@pytest.fixture
def fake_embedding():
    return [0.1] * 384


@pytest.fixture
def mock_embedder(fake_embedding):
    embedder = AsyncMock()
    embedder.embed_text.return_value = fake_embedding
    embedder.embed_texts_batch.return_value = [fake_embedding, fake_embedding]
    return embedder


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.extract_entities_and_triples.side_effect = [
        ExtractionResult(
            entities=[
                RawExtractedEntity(name="Старик", type="Person"),
                RawExtractedEntity(name="Колобок", type="Product"),
            ],
            triples=[
                RawExtractedTriple(
                    subject="Старик", predicate="CREATED", object="Колобок"
                )
            ],
        ),
        ExtractionResult(
            entities=[
                RawExtractedEntity(name="Заяц", type="Animal"),
                RawExtractedEntity(name="Колобок", type="Product"),
            ],
            triples=[
                RawExtractedTriple(
                    subject="Заяц", predicate="INTERACTS_WITH", object="Колобок"
                )
            ],
        ),
    ]
    return llm


@pytest.fixture
def mock_parser():
    parser = MagicMock()
    parser.parse_pdf.return_value = MagicMock()
    parser.chunk_document.return_value = [
        ProcessedChunk(
            index=1,
            enriched_text="Жили-были старик со старухой.",
            metadata=ChunkMetadata(
                chunk_index=1, headings=[], start_page=1, end_page=1
            ),
        ),
        ProcessedChunk(
            index=2,
            enriched_text="Катится колобок, а навстречу ему заяц.",
            metadata=ChunkMetadata(
                chunk_index=2, headings=[], start_page=1, end_page=1
            ),
        ),
    ]
    return parser


@pytest.fixture
def mock_synonym_resolver():
    resolver = AsyncMock()
    resolver.find_synonym_groups.return_value = SynonymResolutionResult()
    return resolver


@pytest.fixture
async def seeded_schema(schema_repo):
    await schema_repo.ensure_indexes()
    await schema_repo.save_tbox_classes(
        [
            SchemaClass(name="Person", status=SchemaStatus.CORE),
            SchemaClass(name="Animal", status=SchemaStatus.CORE),
            SchemaClass(name="Product", status=SchemaStatus.CORE),
        ]
    )
    return schema_repo


class TestIngestHappyPath:
    async def test_ingest_creates_document_chunks_instances_and_triples(
        self,
        seeded_schema,
        doc_repo,
        instance_repo,
        edge_repo,
        mock_parser,
        mock_embedder,
        mock_llm,
        mock_synonym_resolver,
    ):
        er_svc = EntityResolutionOrchestrator(
            instance_repo=instance_repo,
            embedder=mock_embedder,
            matcher=EntityResolutionMatcher(
                levenshtein_threshold=0.85, strict_name_threshold=0.95
            ),
        )
        post_processor = PostProcessingService(
            instance_repo, doc_repo, mock_synonym_resolver, mock_embedder, RAGSettings()
        )

        steps: list[IIngestStep] = [
            EnsureTBoxStep(schema_repo=seeded_schema),
            ParseAndChunkStep(parser=mock_parser),
            EmbedChunksStep(embedder=mock_embedder),
            SaveDocumentStructureStep(doc_repo=doc_repo, edge_repo=edge_repo),
            ExtractEntitiesAndTriplesStep(
                llm=mock_llm,
                schema_repo=seeded_schema,
                instance_repo=instance_repo,
                edge_repo=edge_repo,
                er_svc=er_svc,
            ),
            PostProcessSynonymsStep(post_processor=post_processor),
        ]

        use_case = IngestDocumentUseCase(steps=steps)
        doc_id = await use_case.execute(Path("data/test.pdf"))

        assert len(await doc_repo.get_document_by_filename("test.pdf")) == 1
        assert len(await doc_repo.get_chunks_by_document(doc_id)) == 2
