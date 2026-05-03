# Analytics (GDS)
from .analytics_queries import (
    CleanupSmallCommunitiesQuery,
    DetectCommunitiesQuery,
    DropProjectionQuery,
    GetCommunitiesQuery,
    GetCommunityMembersQuery,
    GraphExistsQuery,
    GraphProjectQuery,
    PersonalizedPageRankQuery,
    SaveCommunitySummaryQuery,
)
from .base import Neo4jQuery

# Document
from .document_queries import (
    GetChunksByDocumentQuery,
    GetDocumentByFilenameQuery,
    SaveChunkQuery,
    SaveDocumentQuery,
)

# Edge
from .edge_queries import SaveEdgeQuery

# Instance
from .instance_queries import (
    DeleteAliasInstancesQuery,
    FindCandidatesByVectorQuery,
    GetAllInstancesQuery,
    GetInstancesByChunkQuery,
    GetInstancesByDocumentQuery,
    GetTriplesByChunkQuery,
    SaveInstanceQuery,
    SaveInstanceRelationQuery,
    TransferAliasIncomingEdgesQuery,
    TransferAliasMentionedInQuery,
    TransferAliasOutgoingEdgesQuery,
    UpdateCanonicalInstanceQuery,
)

# Schema
from .schema_queries import (
    CreateChunkEmbeddingIndexQuery,
    CreateInstanceEmbeddingIndexQuery,
    CreateInstanceNameIndexQuery,
    CreateSchemaClassNameIndexQuery,
    CreateSubclassOfEdgesQuery,
    GetClassUsageCountsQuery,
    GetSchemaRelationsQuery,
    GetTboxClassesQuery,
    SaveSchemaRelationsQuery,
    SaveTboxClassesQuery,
)

__all__ = [
    "CreateChunkEmbeddingIndexQuery",
    # schema
    "CreateInstanceEmbeddingIndexQuery",
    "CreateInstanceNameIndexQuery",
    "CreateSchemaClassNameIndexQuery",
    "CreateSubclassOfEdgesQuery",
    "DeleteAliasInstancesQuery",
    "DetectCommunitiesQuery",
    "DropProjectionQuery",
    "FindCandidatesByVectorQuery",
    "GetAllInstancesQuery",
    "GetChunksByDocumentQuery",
    "GetClassUsageCountsQuery",
    "GetCommunitiesQuery",
    "GetCommunityMembersQuery",
    "GetDocumentByFilenameQuery",
    "GetInstancesByChunkQuery",
    "GetInstancesByDocumentQuery",
    "GetSchemaRelationsQuery",
    "GetTboxClassesQuery",
    "GetTriplesByChunkQuery",
    # analytics
    "GraphExistsQuery",
    "GraphProjectQuery",
    "Neo4jQuery",
    "PersonalizedPageRankQuery",
    "SaveChunkQuery",
    "SaveCommunitySummaryQuery",
    # document
    "SaveDocumentQuery",
    # edge
    "SaveEdgeQuery",
    # instance
    "SaveInstanceQuery",
    "SaveInstanceRelationQuery",
    "SaveSchemaRelationsQuery",
    "SaveTboxClassesQuery",
    "TransferAliasIncomingEdgesQuery",
    "TransferAliasMentionedInQuery",
    "TransferAliasOutgoingEdgesQuery",
    "UpdateCanonicalInstanceQuery",
]
