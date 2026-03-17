from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


class GraphRelationType(str, Enum):
    HAS_CHUNK    = "HAS_CHUNK"
    NEXT_CHUNK   = "NEXT_CHUNK"
    PREV_CHUNK   = "PREV_CHUNK"
    INSTANCE_OF  = "INSTANCE_OF"
    MENTIONED_IN = "MENTIONED_IN"


@dataclass(frozen=True)
class GraphEdge:
    relation_type: GraphRelationType
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
