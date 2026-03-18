"""
Unit: InstanceAggregate — INSTANCE_OF и MENTIONED_IN рёбра.

Поведение:
  - Всегда создаёт ровно 2 ребра
  - INSTANCE_OF ведёт к имени класса (SchemaClass)
  - MENTIONED_IN ведёт к chunk_id
"""

from src.domain.graph_components.nodes import InstanceNode
from src.domain.graph_components.edges import GraphRelationType
from src.domain.agregates.instance_agregate import InstanceAggregate


class TestInstanceAggregateEdges:

    def test_produces_exactly_two_edges(self):
        inst = InstanceNode(
            instance_id="i1", name="Колобок",
            class_name="Product", chunk_id="c1",
        )
        agg = InstanceAggregate(instance=inst)

        edges = agg.build_edges()

        assert len(edges) == 2

    def test_instance_of_points_to_class_name(self):
        inst = InstanceNode(
            instance_id="i1", name="Колобок",
            class_name="Product", chunk_id="c1",
        )
        agg = InstanceAggregate(instance=inst)

        edges = agg.build_edges()

        instance_of = [
            e for e in edges
            if e.relation_type == GraphRelationType.INSTANCE_OF
        ]
        assert len(instance_of) == 1
        assert instance_of[0].source_id == "i1"
        assert instance_of[0].target_id == "Product"

    def test_mentioned_in_points_to_chunk(self):
        inst = InstanceNode(
            instance_id="i1", name="Колобок",
            class_name="Product", chunk_id="c1",
        )
        agg = InstanceAggregate(instance=inst)

        edges = agg.build_edges()

        mentioned = [
            e for e in edges
            if e.relation_type == GraphRelationType.MENTIONED_IN
        ]
        assert len(mentioned) == 1
        assert mentioned[0].source_id == "i1"
        assert mentioned[0].target_id == "c1"