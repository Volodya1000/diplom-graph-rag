from dataclasses import dataclass
from typing import Any

from src.domain.models.community import GraphCommunity

from .base import Neo4jQuery


@dataclass
class GraphExistsQuery(Neo4jQuery[dict[str, Any]]):
    name: str

    def get_query(self) -> str:
        return "CALL gds.graph.exists($name) YIELD exists"

    def get_params(self) -> dict[str, Any]:
        return {"name": self.name}

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return record


@dataclass
class GraphProjectQuery(Neo4jQuery[Any]):
    name: str

    def get_query(self) -> str:
        return """
            CALL gds.graph.project($name, 'Instance', {ALL_RELS: {type: '*', orientation: 'UNDIRECTED'}}, {nodeProperties: ['embedding']})
        """

    def get_params(self) -> dict[str, Any]:
        return {"name": self.name}

    def map_record(self, record: dict[str, Any]) -> Any:
        return None


@dataclass
class DropProjectionQuery(Neo4jQuery[Any]):
    name: str

    def get_query(self) -> str:
        return "CALL gds.graph.drop($name)"

    def get_params(self) -> dict[str, Any]:
        return {"name": self.name}

    def map_record(self, record: dict[str, Any]) -> Any:
        return None


@dataclass
class DetectCommunitiesQuery(Neo4jQuery[dict[str, Any]]):
    projection: str
    prop: str
    algo_call: str

    def get_query(self) -> str:
        return f"CALL {self.algo_call}($projection, {{writeProperty: $prop}}) YIELD communityCount, modularity RETURN communityCount, modularity"

    def get_params(self) -> dict[str, Any]:
        return {"projection": self.projection, "prop": self.prop}

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return record


@dataclass
class GetCommunityMembersQuery(Neo4jQuery[dict[str, Any]]):
    community_id: int

    def get_query(self) -> str:
        return """
            MATCH (i:Instance {community_id: $cid})
            OPTIONAL MATCH (i)-[r]->(other:Instance {community_id: $cid})
            WITH i, collect({predicate: type(r), target: other.name}) AS relations
            RETURN i.instance_id AS instance_id, i.name AS name, i.class_name AS class_name, relations
        """

    def get_params(self) -> dict[str, Any]:
        return {"cid": self.community_id}

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return record


@dataclass
class PersonalizedPageRankQuery(Neo4jQuery[dict[str, Any]]):
    seed_ids: list[str]
    projection: str
    damping: float
    top_k: int

    def get_query(self) -> str:
        return """
            MATCH (seed:Instance)
            WHERE seed.instance_id IN $seed_ids
            WITH collect(seed) AS sourceNodes
            CALL gds.pageRank.stream($projection, {sourceNodes: sourceNodes, dampingFactor: $damping, maxIterations: 20})
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            WHERE node:Instance
            RETURN node.instance_id AS instance_id, node.name AS name, node.class_name AS class_name, node.chunk_id AS chunk_id, score
            ORDER BY score DESC LIMIT $top_k
        """

    def get_params(self) -> dict[str, Any]:
        return {
            "seed_ids": self.seed_ids,
            "projection": self.projection,
            "damping": self.damping,
            "top_k": self.top_k,
        }

    def map_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return record


@dataclass
class CleanupSmallCommunitiesQuery(Neo4jQuery[int]):
    min_size: int

    def get_query(self) -> str:
        return """
            MATCH (i:Instance)
            WHERE i.community_id IS NOT NULL
            WITH i.community_id AS cid, collect(i) AS nodes
            WHERE size(nodes) < $min_size
            UNWIND nodes AS n
            REMOVE n.community_id
            RETURN count(n) AS removed_count
        """

    def get_params(self) -> dict[str, Any]:
        return {"min_size": self.min_size}

    def map_record(self, record: dict[str, Any]) -> int:
        return record.get("removed_count", 0)


@dataclass
class GetCommunitiesQuery(Neo4jQuery[GraphCommunity]):
    def get_query(self) -> str:
        return """
            MATCH (i:Instance)
            WHERE i.community_id IS NOT NULL
            WITH i.community_id AS cid, collect({instance_id: i.instance_id, name: i.name, class_name: i.class_name}) AS members
            OPTIONAL MATCH (cs:CommunitySummary {community_id: cid})
            RETURN cid AS community_id, size(members) AS entity_count, [m IN members | m.name][..10] AS key_entities,
                   cs.name AS name, cs.summary AS summary
            ORDER BY entity_count DESC
        """

    def get_params(self) -> dict[str, Any]:
        return {}

    def map_record(self, record: dict[str, Any]) -> GraphCommunity:
        return GraphCommunity(
            community_id=record["community_id"],
            name=record.get("name"),
            entity_count=record["entity_count"],
            key_entities=record.get("key_entities", []),
            summary=record.get("summary"),
        )


@dataclass
class SaveCommunitySummaryQuery(Neo4jQuery[Any]):
    community_id: int
    summary: str
    key_entities: list[str]
    name: str = ""

    def get_query(self) -> str:
        return "MERGE (cs:CommunitySummary {community_id: $cid}) SET cs.name = $name, cs.summary = $summary, cs.key_entities = $entities, cs.updated_at = datetime()"

    def get_params(self) -> dict[str, Any]:
        return {
            "cid": self.community_id,
            "name": self.name,
            "summary": self.summary,
            "entities": self.key_entities[:20],
        }

    def map_record(self, record: dict[str, Any]) -> Any:
        return None


@dataclass
class GetCommunityDetailsQuery(Neo4jQuery[dict]):
    community_id: int

    def get_query(self) -> str:
        return """
            MATCH (n:Instance {community_id: $cid})
            WITH count(n) AS node_count, collect(n) AS nodes

            OPTIONAL MATCH (cs:CommunitySummary {community_id: $cid})

            CALL {
                WITH nodes
                UNWIND nodes AS n
                MATCH (n)-[r]->(m)
                WHERE m IN nodes
                RETURN count(r) AS edge_count,
                       collect(type(r)) AS raw_rel_types,
                       collect({
                           source: n.name,
                           type: type(r),
                           target: m.name
                       }) AS edges
            }

            CALL {
                WITH nodes
                UNWIND nodes AS n
                OPTIONAL MATCH (n)-[r]-(m)
                WHERE m IN nodes
                RETURN n.name AS hub_name,
                       count(r) AS degree
                ORDER BY degree DESC
                LIMIT 5
            }
            WITH node_count, edge_count, raw_rel_types, edges, cs,
                 collect({name: hub_name, degree: degree}) AS hubs,
                 nodes

            CALL {
                WITH nodes
                UNWIND nodes AS n
                OPTIONAL MATCH (n)-[r]-(m:Instance)
                WHERE coalesce(m.community_id, -1) <> $cid
                WITH n, count(r) AS ext_degree
                WHERE ext_degree > 0
                RETURN n.name AS b_name,
                       ext_degree
                ORDER BY ext_degree DESC
                LIMIT 5
            }
            WITH node_count, edge_count, raw_rel_types, edges, cs, hubs,
                 collect({name: b_name, degree: ext_degree}) AS boundary,
                 nodes

            CALL {
                WITH nodes
                UNWIND nodes AS n
                MATCH (n)-[:MENTIONED_IN]->(:Chunk)<-[:HAS_CHUNK]-(d:Document)
                RETURN count(DISTINCT d) AS doc_count,
                       collect(DISTINCT d.filename) AS docs
            }

            RETURN
                $cid AS community_id,
                cs.name AS name,
                cs.summary AS summary,
                node_count,
                edge_count,
                hubs,
                boundary AS boundary_nodes,
                doc_count,
                docs AS documents,
                [n IN nodes | n.class_name] AS raw_node_types,
                raw_rel_types,
                edges,
                [n IN nodes | {name: n.name, type: n.class_name}] AS node_list
        """

    def get_params(self) -> dict[str, Any]:
        return {"cid": self.community_id}

    def map_record(self, record: dict[str, Any]) -> dict:
        return record
