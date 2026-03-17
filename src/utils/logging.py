"""Утилиты для управления логированием в проекте"""

import logging
import warnings
from typing import Optional


def setup_logging(level: Optional[int] = None, disable_verbose: bool = True):
    """
    Настройка логирования для всего проекта.

    Args:
        level: Уровень логирования (по умолчанию logging.INFO)
        disable_verbose: Отключить многословные логи от библиотек
    """
    if level is None:
        level = logging.INFO

    # Базовая конфигурация
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    if disable_verbose:
        disable_noisy_loggers()


def disable_noisy_loggers():
    """Отключает многословные логи от различных библиотек"""
    noisy_loggers = [
        # Твои основные источники шума
        "src.infrastructure.docling.doc_processor",          # Loading tokenizer / OCR Engine
        "docling.document_converter",
        "docling.models.factories",
        "docling.models.layout_model",
        "docling.pipeline",
        "docling.models.table_structure_model",

        # Transformers / sentence-transformers / tokenizers
        "transformers",
        "transformers.modeling_utils",
        "transformers.tokenization_utils",
        "transformers.utils.logging",               # ← особенно важно для "not sharded" и token length
        "sentence_transformers.SentenceTransformer",
        "tokenizers",

        # HuggingFace общие
        "huggingface_hub.file_download",
        "huggingface_hub.repository",
        "huggingface_hub.hf_api",

        # Остальные (как было раньше)
        "httpx",
        "httpcore",
        "easyocr.easyocr",
        "torch",
        "neo4j",
        "PIL",
        "matplotlib",
        "asyncio",
    ]

    for name in noisy_loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)          # или даже logging.ERROR
        logger.propagate = False

    # Специально для transformers — самый надёжный способ убрать "not sharded" и token length warning
    from transformers.utils import logging as transformers_logging
    transformers_logging.set_verbosity_error()   # или logging.set_verbosity_warning()

    # Подавляем конкретные категории предупреждений
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
    warnings.filterwarnings("ignore", message=".*layers were not sharded.*")
    warnings.filterwarnings("ignore", message=".*Token indices sequence length is longer.*")

def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Получить настроенный логгер.

    Args:
        name: Имя логгера (обычно __name__)
        level: Уровень логирования

    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)

    # Добавляем обработчик, если его нет
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
    """Контекстный менеджер для временного изменения уровня логирования"""

    def __init__(self, logger_name: str, level: int):
        self.logger = logging.getLogger(logger_name)
        self.old_level = self.logger.level
        self.level = level

    def __enter__(self):
        self.logger.setLevel(self.level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.old_level)