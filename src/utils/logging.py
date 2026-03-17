"""Утилиты для управления логированием в проекте"""

import logging
import warnings
from typing import Optional


def setup_logging(level: Optional[int] = None, disable_verbose: bool = True):
    if level is None:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    if disable_verbose:
        disable_noisy_loggers()


def disable_noisy_loggers():
    noisy_loggers = [
        # Docling
        "src.infrastructure.docling.doc_processor",
        "docling.document_converter",
        "docling.models.factories",
        "docling.models.layout_model",
        "docling.pipeline",
        "docling.models.table_structure_model",

        # Transformers
        "transformers",
        "transformers.modeling_utils",
        "transformers.tokenization_utils",
        "transformers.utils.logging",
        "sentence_transformers.SentenceTransformer",
        "tokenizers",

        # HuggingFace
        "huggingface_hub.file_download",
        "huggingface_hub.repository",
        "huggingface_hub.hf_api",

        # HTTP
        "httpx",
        "httpcore",

        # OCR
        "easyocr.easyocr",

        # Neo4j — подавляем warnings о несуществующих свойствах
        "neo4j",
        "neo4j.notifications",
        "neo4j.io",
        "neo4j.pool",

        # Прочие
        "torch",
        "PIL",
        "matplotlib",
        "asyncio",
    ]

    for name in noisy_loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False

    from transformers.utils import logging as transformers_logging
    transformers_logging.set_verbosity_error()

    warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
    warnings.filterwarnings("ignore", message=".*layers were not sharded.*")
    warnings.filterwarnings("ignore", message=".*Token indices sequence length is longer.*")

    # Подавляем neo4j GqlStatusObject warnings
    warnings.filterwarnings("ignore", message=".*Received notification from DBMS.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="neo4j")


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class LoggingContext:
    def __init__(self, logger_name: str, level: int):
        self.logger = logging.getLogger(logger_name)
        self.old_level = self.logger.level
        self.level = level

    def __enter__(self):
        self.logger.setLevel(self.level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)