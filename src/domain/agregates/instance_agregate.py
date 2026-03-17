from dataclasses import dataclass
from typing import List

from domain.graph_components.edges import GraphRelationType, GraphEdge
from domain.graph_components.nodes import InstanceNode


@dataclass
class InstanceAggregate:
    instance: InstanceNode

    def build_edges(self) -> List[GraphEdge]:
        return [
            GraphEdge(
                relation_type=GraphRelationType.INSTANCE_OF,
                source_id=self.instance.instance_id,
                target_id=self.instance.class_name
            ),
            GraphEdge(
                relation_type=GraphRelationType.MENTIONED_IN,
                source_id=self.instance.instance_id,
                target_id=self.instance.chunk_id
            )
        ]
