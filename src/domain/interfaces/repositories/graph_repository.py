"""
DEPRECATED: импортируйте конкретные интерфейсы напрямую.

    from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
    from src.domain.interfaces.repositories.document_repository import IDocumentRepository
    from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
    from src.domain.interfaces.repositories.edge_repository import IEdgeRepository
"""

from src.domain.interfaces.repositories.schema_repository import ISchemaRepository
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.edge_repository import IEdgeRepository

__all__ = [
    "ISchemaRepository",
    "IDocumentRepository",
    "IInstanceRepository",
    "IEdgeRepository",
]