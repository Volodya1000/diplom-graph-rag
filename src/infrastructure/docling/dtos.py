from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChunkMetadata:
    chunk_index: int
    headings: List[str]
    start_page: int
    end_page: int
    doc_hash: Optional[str] = None
    doc_filename: Optional[str] = None

@dataclass
class ProcessedChunk:
    index: int
    enriched_text: str
    metadata: ChunkMetadata