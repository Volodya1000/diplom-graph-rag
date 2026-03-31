"""
Чистые функции-билдеры для создания структурных рёбер графа.
Заменяют логику, которая раньше была в псевдо-агрегатах.
"""

from typing import List
from src.domain.models.edges import GraphRelationType, GraphEdge
from src.domain.models.nodes import DocumentNode, ChunkNode, InstanceNode


class GraphEdgeBuilder:
    @staticmethod
    def build_document_edges(
        document: DocumentNode, chunks: List[ChunkNode]
    ) -> List[GraphEdge]:
        edges: List[GraphEdge] = []

        for chunk in chunks:
            edges.append(
                GraphEdge(
                    relation_type=GraphRelationType.HAS_CHUNK,
                    source_id=document.doc_id,
                    target_id=chunk.chunk_id,
                )
            )

        for i in range(len(chunks) - 1):
            edges.append(
                GraphEdge(
                    relation_type=GraphRelationType.NEXT_CHUNK,
                    source_id=chunks[i].chunk_id,
                    target_id=chunks[i + 1].chunk_id,
                )
            )
            edges.append(
                GraphEdge(
                    relation_type=GraphRelationType.PREV_CHUNK,
                    source_id=chunks[i + 1].chunk_id,
                    target_id=chunks[i].chunk_id,
                )
            )
        return edges

    @staticmethod
    def build_instance_edges(instance: InstanceNode) -> List[GraphEdge]:
        return [
            GraphEdge(
                relation_type=GraphRelationType.INSTANCE_OF,
                source_id=instance.instance_id,
                target_id=instance.class_name,
            ),
            GraphEdge(
                relation_type=GraphRelationType.MENTIONED_IN,
                source_id=instance.instance_id,
                target_id=instance.chunk_id,
            ),
        ]
