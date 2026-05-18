import pytest

from src.domain.models.nodes import ChunkNode, DocumentNode, InstanceNode

pytestmark = pytest.mark.integration


class TestInstanceCRUD:
    async def test_save_and_retrieve_instance_by_chunk(
        self,
        instance_repo,
        doc_repo,
        edge_repo,
        schema_repo,
    ):
        await schema_repo.ensure_indexes()
        doc = DocumentNode(doc_id="d1", filename="t.pdf")
        await doc_repo.save_document(doc)
        chunk = ChunkNode(chunk_id="c1", doc_id="d1", chunk_index=0, text="text")
        await doc_repo.save_chunk(chunk)

        inst = InstanceNode(
            instance_id="i1",
            name="Колобок",
            class_name="Product",
            chunk_id="c1",
            embedding=[0.1] * 384,
        )
        await instance_repo.save_instance(inst)

        from src.domain.services.builders.edge_builder import GraphEdgeBuilder

        await edge_repo.save_edges(GraphEdgeBuilder.build_instance_edges(inst))

        result = await instance_repo.get_instances_by_chunk("c1")
        assert len(result) == 1
        assert result[0].name == "Колобок"

    async def test_get_triples_by_chunk_uses_mentioned_in_edges(
        self,
        instance_repo,
        doc_repo,
        edge_repo,
        schema_repo,
    ):
        """Проверяет, что триплеты находятся через структурные связи MENTIONED_IN, а не через свойство ребра."""
        await schema_repo.ensure_indexes()

        # 1. Создаем чанк
        doc = DocumentNode(doc_id="d1", filename="triples_test.pdf")
        await doc_repo.save_document(doc)
        chunk = ChunkNode(chunk_id="c1", doc_id="d1", chunk_index=0, text="text")
        await doc_repo.save_chunk(chunk)

        # 2. Создаем две сущности
        inst1 = InstanceNode(instance_id="i1", name="Субъект", class_name="Person", chunk_id="c1")
        inst2 = InstanceNode(instance_id="i2", name="Объект", class_name="Organization", chunk_id="c1")
        await instance_repo.save_instance(inst1)
        await instance_repo.save_instance(inst2)

        # 3. Привязываем обе сущности к чанку
        from src.domain.models.edges import GraphEdge, GraphRelationType

        edges = [
            GraphEdge(relation_type=GraphRelationType.MENTIONED_IN, source_id="i1", target_id="c1"),
            GraphEdge(relation_type=GraphRelationType.MENTIONED_IN, source_id="i2", target_id="c1"),
        ]
        await edge_repo.save_edges(edges)

        # 4. Создаем связь между ними напрямую (БЕЗ свойства chunk_id, чтобы проверить новую логику)
        async with instance_repo._sm.session() as s:
            await s.run(
                "MATCH (a:Instance {instance_id: 'i1'}), (b:Instance {instance_id: 'i2'}) MERGE (a)-[:WORKS_AT]->(b)"
            )

        # 5. Вызываем метод репозитория
        triples = await instance_repo.get_triples_by_chunk("c1")

        assert len(triples) == 1
        assert triples[0]["subject_name"] == "Субъект"
        assert triples[0]["predicate"] == "WORKS_AT"
        assert triples[0]["object_name"] == "Объект"
