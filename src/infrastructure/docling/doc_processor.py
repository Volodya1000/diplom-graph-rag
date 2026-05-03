from typing import Any

from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

from src.config.chunking_settings import ChunkingSettings
from src.config.parsing_settings import ParsingSettings
from src.utils.logging import get_logger

from .dtos import ChunkMetadata, ProcessedChunk
from .pdf_pipeline_options_factory import build_pipeline_options
from .text_cleaner import TextCleaner

logger = get_logger(__name__)


class DocProcessor:
    def __init__(self, chunking_settings: ChunkingSettings, parsing_settings: ParsingSettings) -> None:
        self.logger = logger
        self.chunking_settings = chunking_settings
        self.parsing_settings = parsing_settings

        # 1. Инициализация Токенайзера (из ChunkingSettings)
        self.logger.info(f"Loading tokenizer: {self.chunking_settings.tokenizer_model}")
        self.tokenizer = HuggingFaceTokenizer.from_pretrained(
            model_name=self.chunking_settings.tokenizer_model,
            max_tokens=self.chunking_settings.max_tokens,
        )

        # 2. Сборка пайплайна Docling через Factory (из ParsingSettings)
        pipeline_options = build_pipeline_options(self.parsing_settings)
        self.logger.info(f"OCR Engine selected: {self.parsing_settings.ocr_engine}")

        # 3. Инициализация конвертера
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            },
        )

    def parse_pdf(self, path: str):
        """Парсит PDF в структуру Docling (Неизменная логика)."""
        self.logger.info(f"Parsing PDF: {path}")
        result = self.converter.convert(path)
        return result.document

    def get_document_preview(self, doc, max_pages: int = 2) -> str:
        """Быстрое превью документа."""
        # Используем логику из вашего второго сниппета, она быстрее для превью
        preview_parts = []
        # Проверка на наличие текстов (в разных версиях docling структура может отличаться)
        if hasattr(doc, "texts"):
            for item in doc.texts:
                if item.prov and hasattr(item.prov[0], "page_no") and item.prov[0].page_no <= max_pages:
                    clean_part = TextCleaner.clean(item.text)
                    if clean_part:
                        preview_parts.append(clean_part)
        else:
            # Fallback на markdown экспорт, если структура иная
            md_text = doc.export_to_markdown()
            lines = md_text.split("\n")
            return "\n".join(lines[:100])

        return "\n".join(preview_parts)

    def _extract_chunk_metadata(
        self, docling_chunk: Any, chunk_index: int, override_filename: str | None = None
    ) -> ChunkMetadata:
        meta = docling_chunk.meta
        headings = [TextCleaner.clean(h) for h in (meta.headings or []) if h]

        page_numbers = set()
        # Универсальный обход provenance
        for doc_item in meta.doc_items:
            if hasattr(doc_item, "prov") and doc_item.prov:
                # Обработка списка или одиночного объекта
                provs = doc_item.prov if isinstance(doc_item.prov, list) else [doc_item.prov]
                for prov in provs:
                    if hasattr(prov, "page_no"):
                        page_numbers.add(prov.page_no)

        start_page = min(page_numbers) if page_numbers else 0
        end_page = max(page_numbers) if page_numbers else 0

        doc_hash = None
        if override_filename:
            doc_filename = override_filename
        elif meta.origin:
            doc_filename = meta.origin.filename
        else:
            doc_filename = None

        if hasattr(meta, "origin") and meta.origin:
            doc_hash = str(meta.origin.binary_hash) if hasattr(meta.origin, "binary_hash") else None

        return ChunkMetadata(
            chunk_index=chunk_index,
            headings=headings,
            start_page=start_page,
            end_page=end_page,
            doc_hash=doc_hash,
            doc_filename=doc_filename,
        )

    def chunk_document(self, doc, override_filename: str | None = None) -> list[ProcessedChunk]:
        chunker = HybridChunker(
            tokenizer=self.tokenizer,
            merge_peers=self.chunking_settings.merge_peers,
        )

        processed_chunks = []

        # Docling сам отдаст уже нужные плотные блоки
        for i, docling_chunk in enumerate(chunker.chunk(dl_doc=doc), start=1):
            # contextualize() уже включает в себя добавление заголовков из метаданных в текст
            enriched_text = chunker.contextualize(chunk=docling_chunk)

            if not enriched_text or not enriched_text.strip():
                continue

            metadata = self._extract_chunk_metadata(docling_chunk, i, override_filename)

            processed_chunks.append(
                ProcessedChunk(
                    index=i,
                    enriched_text=enriched_text,
                    metadata=metadata,
                ),
            )

        self.logger.info(f"Document split into {len(processed_chunks)} chunks")
        return processed_chunks
