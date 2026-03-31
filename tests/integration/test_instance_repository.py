import pytest
from src.domain.models.nodes import InstanceNode, ChunkNode, DocumentNode

pytestmark = pytest.mark.integration


class TestInstanceCRUD:
    async def test_save_and_retrieve_instance_by_chunk(
        self, instance_repo, doc_repo, edge_repo, schema_repo
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
