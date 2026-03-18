"""
Integration: IngestDocumentUseCase — happy path через все слои.

Проверяет полный пайплайн: parse → embed → save → extract → resolve.

LLM и Embedder — неуправляемые зависимости (внешние API),
поэтому мокируются на границе системы.
DocProcessor — тяжёлая инфра, мокируется.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from src.domain.ontology.shema import SchemaClass, SchemaStatus
from src.domain.interfaces.llm.llm_client import ExtractionResult
from src.application.dtos.extraction_dtos import RawExtractedEntity, RawExtractedTriple
from src.application.use_cases.ingest_document import IngestDocumentUseCase
from src.application.services.entity_resolution_service import EntityResolutionOrchestrator
from src.application.services.post_processing_service import PostProcessingService
from src.domain.resolution_rules import EntityResolutionMatcher
from src.domain.value_objects.synonym_group import SynonymResolutionResult
from src.infrastructure.docling.dtos import ProcessedChunk, ChunkMetadata


pytestmark = pytest.mark.integration


@pytest.fixture
def fake_embedding():
    """384-мерный вектор для тестов."""
    return [0.1] * 384


@pytest.fixture
def mock_embedder(fake_embedding):
    """Стаб эмбеддера — неуправляемая зависимость."""
    embedder = AsyncMock()
    embedder.embed_text.return_value = fake_embedding
    embedder.embed_texts_batch.return_value = [fake_embedding, fake_embedding]
    return embedder


@pytest.fixture
def mock_llm():
    """
    Стаб LLM — неуправляемая зависимость.
    Возвращает фиксированные сущности и тройки.
    """
    llm = AsyncMock()

    # Первый чанк: Старик, Старуха, Колобок
    extraction_1 = ExtractionResult(
        entities=[
            RawExtractedEntity(name="Старик", type="Person"),
            RawExtractedEntity(name="Старуха", type="Person"),
            RawExtractedEntity(name="Колобок", type="Product"),
        ],
        triples=[
            RawExtractedTriple(
                subject="Старуха", predicate="CREATED", object="Колобок",
            ),
        ],
    )

    # Второй чанк: Заяц
    extraction_2 = ExtractionResult(
        entities=[
            RawExtractedEntity(name="Заяц", type="Animal"),
            RawExtractedEntity(name="Колобок", type="Product"),
        ],
        triples=[
            RawExtractedTriple(
                subject="Заяц", predicate="INTERACTS_WITH", object="Колобок",
            ),
        ],
    )

    llm.extract_entities_and_triples.side_effect = [extraction_1, extraction_2]
    return llm


@pytest.fixture
def mock_parser():
    """Стаб парсера — тяжёлая инфра-зависимость."""
    parser = MagicMock()
    parser.parse_pdf.return_value = MagicMock()
    parser.chunk_document.return_value = [
        ProcessedChunk(
            index=1,
            enriched_text="Жили-были старик со старухой. Испекла старуха колобок.",
            metadata=ChunkMetadata(
                chunk_index=1, headings=[], start_page=1, end_page=1,
            ),
        ),
        ProcessedChunk(
            index=2,
            enriched_text="Катится колобок, а навстречу ему заяц.",
            metadata=ChunkMetadata(
                chunk_index=2, headings=[], start_page=1, end_page=1,
            ),
        ),
    ]
    return parser


@pytest.fixture
def mock_synonym_resolver():
    """Стаб synonym resolver — неуправляемая зависимость."""
    resolver = AsyncMock()
    resolver.find_synonym_groups.return_value = SynonymResolutionResult()
    return resolver


@pytest.fixture
async def seeded_schema(schema_repo):
    """T-Box с базовыми классами для теста."""
    await schema_repo.ensure_indexes()
    await schema_repo.save_tbox_classes([
        SchemaClass(name="Person", status=SchemaStatus.CORE),
        SchemaClass(name="Animal", status=SchemaStatus.CORE),
        SchemaClass(name="Product", status=SchemaStatus.CORE),
    ])
    from src.domain.ontology.shema import SchemaRelation
    await schema_repo.save_schema_relations([
        SchemaRelation(
            source_class="Person", relation_name="CREATED",
            target_class="Product", status=SchemaStatus.CORE,
        ),
        SchemaRelation(
            source_class="Animal", relation_name="INTERACTS_WITH",
            target_class="Product", status=SchemaStatus.CORE,
        ),
    ])
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
        # Arrange
        matcher = EntityResolutionMatcher(levenshtein_threshold=0.85)
        er_svc = EntityResolutionOrchestrator(
            instance_repo=instance_repo,
            embedder=mock_embedder,
            matcher=matcher,
        )
        post_processor = PostProcessingService(
            instance_repo=instance_repo,
            doc_repo=doc_repo,
            synonym_resolver=mock_synonym_resolver,
            embedder=mock_embedder,
        )
        use_case = IngestDocumentUseCase(
            parser=mock_parser,
            schema_repo=seeded_schema,
            doc_repo=doc_repo,
            instance_repo=instance_repo,
            edge_repo=edge_repo,
            embedder=mock_embedder,
            llm=mock_llm,
            er_svc=er_svc,
            post_processor=post_processor,
        )

        # Act
        doc_id = await use_case.execute(Path("data/test.pdf"))

        # Assert — проверяем состояние БД отдельными запросами

        # Документ создан
        docs = await doc_repo.get_document_by_filename("test.pdf")
        assert len(docs) == 1
        assert docs[0].doc_id == doc_id

        # 2 чанка сохранены
        chunks = await doc_repo.get_chunks_by_document(doc_id)
        assert len(chunks) == 2
        assert chunks[0].chunk_index == 1
        assert chunks[1].chunk_index == 2

        # Сущности созданы (минимум 3 уникальных: Старик, Старуха, Колобок, Заяц)
        all_instances_c1 = await instance_repo.get_instances_by_chunk(
            chunks[0].chunk_id,
        )
        all_instances_c2 = await instance_repo.get_instances_by_chunk(
            chunks[1].chunk_id,
        )
        total_unique_names = {
            i.name for i in all_instances_c1 + all_instances_c2
        }
        assert "Старик" in total_unique_names or "Старуха" in total_unique_names
        assert "Колобок" in total_unique_names
        assert len(total_unique_names) >= 3

        # Тройки созданы
        triples_c1 = await instance_repo.get_triples_by_chunk(
            chunks[0].chunk_id,
        )
        assert len(triples_c1) >= 1
        predicates = {t["predicate"] for t in triples_c1}
        assert "CREATED" in predicates

    async def test_ingest_is_idempotent_for_different_files(
        self,
        seeded_schema,
        doc_repo,
        instance_repo,
        edge_repo,
        mock_embedder,
        mock_synonym_resolver,
    ):
        """Два разных файла создают два разных документа."""
        # Arrange
        matcher = EntityResolutionMatcher(levenshtein_threshold=0.85)
        er_svc = EntityResolutionOrchestrator(
            instance_repo=instance_repo,
            embedder=mock_embedder,
            matcher=matcher,
        )
        post_processor = PostProcessingService(
            instance_repo=instance_repo,
            doc_repo=doc_repo,
            synonym_resolver=mock_synonym_resolver,
            embedder=mock_embedder,
        )

        def make_parser(filename: str):
            parser = MagicMock()
            parser.parse_pdf.return_value = MagicMock()
            parser.chunk_document.return_value = [
                ProcessedChunk(
                    index=1,
                    enriched_text=f"Content of {filename}",
                    metadata=ChunkMetadata(
                        chunk_index=1, headings=[],
                        start_page=1, end_page=1,
                    ),
                ),
            ]
            return parser

        llm1 = AsyncMock()
        llm1.extract_entities_and_triples.return_value = ExtractionResult(
            entities=[RawExtractedEntity(name="Entity1", type="Person")],
            triples=[],
        )
        llm2 = AsyncMock()
        llm2.extract_entities_and_triples.return_value = ExtractionResult(
            entities=[RawExtractedEntity(name="Entity2", type="Person")],
            triples=[],
        )

        mock_embedder.embed_texts_batch.return_value = [[0.1] * 384]

        uc1 = IngestDocumentUseCase(
            parser=make_parser("a.pdf"),
            schema_repo=seeded_schema,
            doc_repo=doc_repo,
            instance_repo=instance_repo,
            edge_repo=edge_repo,
            embedder=mock_embedder,
            llm=llm1,
            er_svc=er_svc,
            post_processor=post_processor,
        )
        uc2 = IngestDocumentUseCase(
            parser=make_parser("b.pdf"),
            schema_repo=seeded_schema,
            doc_repo=doc_repo,
            instance_repo=instance_repo,
            edge_repo=edge_repo,
            embedder=mock_embedder,
            llm=llm2,
            er_svc=er_svc,
            post_processor=post_processor,
        )

        # Act
        id1 = await uc1.execute(Path("data/a.pdf"))
        id2 = await uc2.execute(Path("data/b.pdf"))

        # Assert
        assert id1 != id2
        docs_a = await doc_repo.get_document_by_filename("a.pdf")
        docs_b = await doc_repo.get_document_by_filename("b.pdf")
        assert len(docs_a) == 1
        assert len(docs_b) == 1