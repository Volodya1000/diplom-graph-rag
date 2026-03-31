from .base import Neo4jQuery

# Document
from .document_queries import (
    SaveDocumentQuery,
    SaveChunkQuery,
    GetDocumentByFilenameQuery,
    GetChunksByDocumentQuery,
)

# Instance
from .instance_queries import (
    SaveInstanceQuery,
    SaveInstanceRelationQuery,
    FindCandidatesByVectorQuery,
    GetInstancesByChunkQuery,
    GetTriplesByChunkQuery,
    GetInstancesByDocumentQuery,
    GetAllInstancesQuery,
    TransferAliasIncomingEdgesQuery,
    TransferAliasOutgoingEdgesQuery,
    TransferAliasMentionedInQuery,
    UpdateCanonicalInstanceQuery,
    DeleteAliasInstancesQuery,
)

# Edge
from .edge_queries import SaveEdgeQuery

# Schema
from .schema_queries import (
    CreateInstanceEmbeddingIndexQuery,
    CreateChunkEmbeddingIndexQuery,
    CreateInstanceNameIndexQuery,
    CreateSchemaClassNameIndexQuery,
    GetTboxClassesQuery,
    SaveTboxClassesQuery,
    CreateSubclassOfEdgesQuery,
    GetSchemaRelationsQuery,
    SaveSchemaRelationsQuery,
    GetClassUsageCountsQuery,
)

# Analytics (GDS)
from .analytics_queries import (
    GraphExistsQuery,
    GraphProjectQuery,
    DropProjectionQuery,
    DetectCommunitiesQuery,
    GetCommunitiesQuery,
    GetCommunityMembersQuery,
    SaveCommunitySummaryQuery,
    PersonalizedPageRankQuery,
)

__all__ = [
    "Neo4jQuery",
    # document
    "SaveDocumentQuery",
    "SaveChunkQuery",
    "GetDocumentByFilenameQuery",
    "GetChunksByDocumentQuery",
    # instance
    "SaveInstanceQuery",
    "SaveInstanceRelationQuery",
    "FindCandidatesByVectorQuery",
    "GetInstancesByChunkQuery",
    "GetTriplesByChunkQuery",
    "GetInstancesByDocumentQuery",
    "GetAllInstancesQuery",
    "TransferAliasIncomingEdgesQuery",
    "TransferAliasOutgoingEdgesQuery",
    "TransferAliasMentionedInQuery",
    "UpdateCanonicalInstanceQuery",
    "DeleteAliasInstancesQuery",
    # edge
    "SaveEdgeQuery",
    # schema
    "CreateInstanceEmbeddingIndexQuery",
    "CreateChunkEmbeddingIndexQuery",
    "CreateInstanceNameIndexQuery",
    "CreateSchemaClassNameIndexQuery",
    "GetTboxClassesQuery",
    "SaveTboxClassesQuery",
    "CreateSubclassOfEdgesQuery",
    "GetSchemaRelationsQuery",
    "SaveSchemaRelationsQuery",
    "GetClassUsageCountsQuery",
    # analytics
    "GraphExistsQuery",
    "GraphProjectQuery",
    "DropProjectionQuery",
    "DetectCommunitiesQuery",
    "GetCommunitiesQuery",
    "GetCommunityMembersQuery",
    "SaveCommunitySummaryQuery",
    "PersonalizedPageRankQuery",
]
