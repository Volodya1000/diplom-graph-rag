from dataclasses import dataclass
from typing import Dict, Any, List
from .base import Neo4jQuery


@dataclass
class GraphExistsQuery(Neo4jQuery):
    name: str

    def get_query(self) -> str:
        return """
            CALL gds.graph.exists($name) YIELD exists
        """

    def get_params(self) -> Dict[str, Any]:
        return {"name": self.name}


@dataclass
class GraphProjectQuery(Neo4jQuery):
    name: str

    def get_query(self) -> str:
        return """
            CALL gds.graph.project(
                $name,
                'Instance',
                {
                    ALL_RELS: {
                        type: '*',
                        orientation: 'UNDIRECTED'
                    }
                },
                {
                    nodeProperties: ['embedding']
                }
            )
        """

    def get_params(self) -> Dict[str, Any]:
        return {"name": self.name}


@dataclass
class DropProjectionQuery(Neo4jQuery):
    name: str

    def get_query(self) -> str:
        return """
            CALL gds.graph.drop($name)
        """

    def get_params(self) -> Dict[str, Any]:
        return {"name": self.name}


@dataclass
class DetectCommunitiesQuery(Neo4jQuery):
    projection: str
    prop: str
    algo_call: str

    def get_query(self) -> str:
        return f"""
            CALL {self.algo_call}(
                $projection,
                {{writeProperty: $prop}}
            )
            YIELD communityCount, modularity
            RETURN communityCount, modularity
        """

    def get_params(self) -> Dict[str, Any]:
        return {"projection": self.projection, "prop": self.prop}


@dataclass
class GetCommunitiesQuery(Neo4jQuery):
    def get_query(self) -> str:
        return """
            MATCH (i:Instance)
            WHERE i.community_id IS NOT NULL
            WITH i.community_id AS cid,
                 collect({
                     instance_id: i.instance_id,
                     name: i.name,
                     class_name: i.class_name
                 }) AS members
            OPTIONAL MATCH (cs:CommunitySummary {community_id: cid})
            RETURN cid AS community_id,
                   size(members) AS entity_count,
                   [m IN members | m.name][..10] AS key_entities,
                   cs.summary AS summary
            ORDER BY entity_count DESC
        """

    def get_params(self) -> Dict[str, Any]:
        return {}


@dataclass
class GetCommunityMembersQuery(Neo4jQuery):
    community_id: int

    def get_query(self) -> str:
        return """
            MATCH (i:Instance {community_id: $cid})
            OPTIONAL MATCH (i)-[r]->(other:Instance {community_id: $cid})
            WITH i, collect({
                predicate: type(r),
                target: other.name
            }) AS relations
            RETURN i.instance_id AS instance_id,
                   i.name AS name,
                   i.class_name AS class_name,
                   relations
        """

    def get_params(self) -> Dict[str, Any]:
        return {"cid": self.community_id}


@dataclass
class SaveCommunitySummaryQuery(Neo4jQuery):
    community_id: int
    summary: str
    key_entities: List[str]

    def get_query(self) -> str:
        return """
            MERGE (cs:CommunitySummary {community_id: $cid})
            SET cs.summary = $summary,
                cs.key_entities = $entities,
                cs.updated_at = datetime()
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "cid": self.community_id,
            "summary": self.summary,
            "entities": self.key_entities[:20],
        }


@dataclass
class PersonalizedPageRankQuery(Neo4jQuery):
    seed_ids: List[str]
    projection: str
    damping: float
    top_k: int

    def get_query(self) -> str:
        return """
            MATCH (seed:Instance)
            WHERE seed.instance_id IN $seed_ids
            WITH collect(seed) AS sourceNodes
            CALL gds.pageRank.stream($projection, {
                sourceNodes: sourceNodes,
                dampingFactor: $damping,
                maxIterations: 20
            })
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            WHERE node:Instance
            RETURN node.instance_id AS instance_id,
                   node.name AS name,
                   node.class_name AS class_name,
                   node.chunk_id AS chunk_id,
                   score
            ORDER BY score DESC
            LIMIT $top_k
        """

    def get_params(self) -> Dict[str, Any]:
        return {
            "seed_ids": self.seed_ids,
            "projection": self.projection,
            "damping": self.damping,
            "top_k": self.top_k,
        }