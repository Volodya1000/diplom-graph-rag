"""Integration: DeleteDocumentUseCase и логика безопасного удаления в Cypher."""

from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.delete_document_use_case import DeleteDocumentUseCase
from src.domain.models.extraction import ResolvedTriple
from src.domain.models.nodes import ChunkNode, DocumentNode, InstanceNode
from src.domain.services.builders.edge_builder import GraphEdgeBuilder

pytestmark = pytest.mark.integration


class TestDeleteDocumentIntegration:
    async def test_safe_deletion_with_shared_instances(
        self,
        doc_repo,
        instance_repo,
        edge_repo,
        schema_repo,
    ):
        """
        СЦЕНАРИЙ:
        - Doc A: имеет Сущность 1 и Сущность 2. Связь "1 -> 2"
        - Doc B: имеет Сущность 2 и Сущность 3. Связь "2 -> 3"
        - Удаляем Doc A.
        ОЖИДАЕМ:
        - Doc A и его чанки удалены.
        - Сущность 1 удалена (она изолированная).
        - Связь "1 -> 2" удалена.
        - Сущность 2 ОСТАВЛЕНА (так как она есть в Doc B).
        - Сущность 3 ОСТАВЛЕНА.
        - Doc B и его чанки ОСТАВЛЕНЫ.
        """
        await schema_repo.ensure_indexes()

        # Создаем Doc A и Doc B
        doc_a = DocumentNode(doc_id="doc_a", filename="file_A.pdf")
        doc_b = DocumentNode(doc_id="doc_b", filename="file_B.pdf")
        await doc_repo.save_document(doc_a)
        await doc_repo.save_document(doc_b)

        # Создаем чанки
        chunk_a = ChunkNode(chunk_id="chunk_a", doc_id="doc_a", chunk_index=0, text="A")
        chunk_b = ChunkNode(chunk_id="chunk_b", doc_id="doc_b", chunk_index=0, text="B")
        await doc_repo.save_chunk(chunk_a)
        await doc_repo.save_chunk(chunk_b)

        await edge_repo.save_edges(GraphEdgeBuilder.build_document_edges(doc_a, [chunk_a]))
        await edge_repo.save_edges(GraphEdgeBuilder.build_document_edges(doc_b, [chunk_b]))

        # Создаем сущности
        inst1 = InstanceNode(instance_id="i1", name="Isolated A", class_name="Person", chunk_id="chunk_a")
        inst2 = InstanceNode(instance_id="i2", name="Shared", class_name="Person", chunk_id="chunk_a")
        inst3 = InstanceNode(instance_id="i3", name="Isolated B", class_name="Person", chunk_id="chunk_b")
        for i in (inst1, inst2, inst3):
            await instance_repo.save_instance(i)

        # Связываем сущности с чанками (MENTIONED_IN)
        await edge_repo.save_edges(GraphEdgeBuilder.build_instance_edges(inst1))  # В chunk_a
        await edge_repo.save_edges(GraphEdgeBuilder.build_instance_edges(inst2))  # В chunk_a

        # Добавляем inst2 еще и в chunk_b
        inst2_in_b = InstanceNode(
            instance_id=inst2.instance_id, name=inst2.name, class_name=inst2.class_name, chunk_id="chunk_b"
        )
        await edge_repo.save_edges(GraphEdgeBuilder.build_instance_edges(inst2_in_b))

        await edge_repo.save_edges(GraphEdgeBuilder.build_instance_edges(inst3))  # В chunk_b

        # Создаем триплеты
        await instance_repo.save_instance_relation(
            ResolvedTriple(source_instance_id="i1", target_instance_id="i2", relation_name="KNOWS", chunk_id="chunk_a")
        )
        await instance_repo.save_instance_relation(
            ResolvedTriple(source_instance_id="i2", target_instance_id="i3", relation_name="KNOWS", chunk_id="chunk_b")
        )

        # Подготавливаем Use Case
        mock_file_storage = AsyncMock()
        mock_file_storage.delete_file.return_value = True
        use_case = DeleteDocumentUseCase(doc_repo, mock_file_storage)

        # === ВЫПОЛНЕНИЕ ===
        result = await use_case.execute("file_A.pdf")

        # === ПРОВЕРКИ ===
        assert result is True

        # Doc A и Chunk A удалены
        assert len(await doc_repo.get_document_by_filename("file_A.pdf")) == 0
        assert len(await doc_repo.get_chunks_by_document("doc_a")) == 0

        # Doc B и Chunk B целы
        assert len(await doc_repo.get_document_by_filename("file_B.pdf")) == 1
        assert len(await doc_repo.get_chunks_by_document("doc_b")) == 1

        # Инстанс 1 удален, Инстансы 2 и 3 целы
        all_instances = await instance_repo.get_all_instances()
        all_ids = {i.instance_id for i in all_instances}
        assert "i1" not in all_ids
        assert "i2" in all_ids
        assert "i3" in all_ids

        # Триплет из Doc A удален, из Doc B цел
        triples_b = await instance_repo.get_triples_by_chunk("chunk_b")
        assert len(triples_b) == 1
        assert triples_b[0]["subject_name"] == "Shared"

    async def test_delete_empty_document(self, doc_repo, schema_repo):
        """Удаление пустого документа (без чанков и сущностей) работает корректно."""
        await schema_repo.ensure_indexes()
        doc = DocumentNode(doc_id="empty", filename="empty.pdf")
        await doc_repo.save_document(doc)

        mock_fs = AsyncMock()
        use_case = DeleteDocumentUseCase(doc_repo, mock_fs)

        result = await use_case.execute("empty.pdf")

        assert result is True
        assert len(await doc_repo.get_document_by_filename("empty.pdf")) == 0

    async def test_delete_nonexistent_document_does_not_break(self, doc_repo):
        """Удаление несуществующего документа не ломает базу."""
        mock_fs = AsyncMock()
        mock_fs.delete_file.return_value = False
        use_case = DeleteDocumentUseCase(doc_repo, mock_fs)

        result = await use_case.execute("ghost.pdf")

        assert result is False
