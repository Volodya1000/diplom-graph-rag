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

    # Список логгеров для отключения/уменьшения
    noisy_loggers = [
        # Docling
        "docling.datamodel",
        "docling.document_converter",
        "docling.models.factories",
        "docling.utils.accelerator_utils",
        "docling.models.layout_model",
        "docling.pipeline",
        "docling.models.table_structure_model",

        # HTTPX (используется некоторыми библиотеками)
        "httpx",
        "httpcore",

        # HuggingFace
        "huggingface_hub.file_download",
        "huggingface_hub.repository",
        "huggingface_hub.hf_api",
        "urllib3.connectionpool",
        "filelock",

        # EasyOCR
        "easyocr.easyocr",

        # Transformers
        "transformers",
        "transformers.modeling_utils",
        "transformers.tokenization_utils",

        # Sentence Transformers
        "sentence_transformers.SentenceTransformer",

        # PyTorch
        "torch",
        "torch.distributed",

        # Neo4j
        "neo4j",
        "neo4j.pool",

        # Общие
        "PIL",
        "matplotlib",
        "asyncio",
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)  # Только предупреждения и ошибки
        logger.propagate = False  # Не передавать сообщения выше

    # Отключаем конкретные предупреждения
    warnings.filterwarnings("ignore", category=UserWarning, module="torch")
    warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
    warnings.filterwarnings("ignore", message="Xet Storage is enabled")


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