"""
Integration: Neo4jInstanceRepository — instances, vector search, relations.
"""

import pytest
from src.domain.graph_components.nodes import InstanceNode, ChunkNode, DocumentNode
from src.application.dtos.extraction_dtos import ResolvedTriple


pytestmark = pytest.mark.integration


class TestInstanceCRUD:

    async def test_save_and_retrieve_instance_by_chunk(
        self, instance_repo, doc_repo, edge_repo, schema_repo,
    ):
        await schema_repo.ensure_indexes()
        await schema_repo.save_tbox_classes([
            pytest.importorskip("src.domain.ontology.shema").SchemaClass(
                name="Person", status="core",
            ),
        ])

        doc = DocumentNode(doc_id="d1", filename="t.pdf")
        await doc_repo.save_document(doc)
        chunk = ChunkNode(
            chunk_id="c1", doc_id="d1", chunk_index=0, text="text",
        )
        await doc_repo.save_chunk(chunk)

        inst = InstanceNode(
            instance_id="i1", name="Колобок",
            class_name="Person", chunk_id="c1",
            embedding=[0.1] * 384,
        )
        await instance_repo.save_instance(inst)

        # Создаём MENTIONED_IN ребро
        from src.domain.agregates.instance_agregate import InstanceAggregate
        agg = InstanceAggregate(instance=inst)
        await edge_repo.save_edges(agg.build_edges())

        result = await instance_repo.get_instances_by_chunk("c1")
        assert len(result) == 1
        assert result[0].name == "Колобок"


class TestVectorSearch:

    async def test_vector_search_finds_similar_instance(
        self, instance_repo, schema_repo,
    ):
        await schema_repo.ensure_indexes()
        embedding = [0.5] * 384

        inst = InstanceNode(
            instance_id="i1", name="Тест",
            class_name="Concept", chunk_id="c1",
            embedding=embedding,
        )
        await instance_repo.save_instance(inst)

        # Ищем похожий вектор
        candidates = await instance_repo.find_candidates_by_vector(
            embedding=embedding, limit=5,
        )

        assert len(candidates) >= 1
        assert candidates[0].name == "Тест"


class TestInstanceRelations:

    async def test_save_and_retrieve_triple(
        self, instance_repo, schema_repo,
    ):
        await schema_repo.ensure_indexes()

        src = InstanceNode(
            instance_id="i1", name="A", class_name="Person",
            chunk_id="c1", embedding=[0.1] * 384,
        )
        tgt = InstanceNode(
            instance_id="i2", name="B", class_name="Person",
            chunk_id="c1", embedding=[0.2] * 384,
        )
        await instance_repo.save_instance(src)
        await instance_repo.save_instance(tgt)

        triple = ResolvedTriple(
            source_instance_id="i1", relation_name="KNOWS",
            target_instance_id="i2", chunk_id="c1",
        )
        await instance_repo.save_instance_relation(triple)

        triples = await instance_repo.get_triples_by_chunk("c1")
        assert len(triples) == 1
        assert triples[0]["predicate"] == "KNOWS"
        assert triples[0]["subject_name"] == "A"
        assert triples[0]["object_name"] == "B"