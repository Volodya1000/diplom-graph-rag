from dataclasses import dataclass
from typing import List

from src.domain.graph_components.edges import GraphRelationType, GraphEdge
from src.domain.graph_components.nodes import DocumentNode, ChunkNode


@dataclass
class DocumentAggregate:
    document: DocumentNode
    chunks: List[ChunkNode]

    def build_edges(self) -> List[GraphEdge]:
        edges: List[GraphEdge] = []

        for chunk in self.chunks:
            edges.append(GraphEdge(
                relation_type=GraphRelationType.HAS_CHUNK,
                source_id=self.document.doc_id,
                target_id=chunk.chunk_id
            ))

        for i in range(len(self.chunks) - 1):
            edges.append(GraphEdge(
                relation_type=GraphRelationType.NEXT_CHUNK,
                source_id=self.chunks[i].chunk_id,
                target_id=self.chunks[i + 1].chunk_id
            ))
            edges.append(GraphEdge(
                relation_type=GraphRelationType.PREV_CHUNK,
                source_id=self.chunks[i + 1].chunk_id,
                target_id=self.chunks[i].chunk_id
            ))
        return edges
