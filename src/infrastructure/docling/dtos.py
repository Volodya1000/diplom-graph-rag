from dataclasses import dataclass


@dataclass
class ChunkMetadata:
    chunk_index: int
    headings: list[str]
    start_page: int
    end_page: int
    doc_hash: str | None = None
    doc_filename: str | None = None


@dataclass
class ProcessedChunk:
    index: int
    enriched_text: str
    metadata: ChunkMetadata
