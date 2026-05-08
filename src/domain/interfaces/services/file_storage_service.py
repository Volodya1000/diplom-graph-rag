from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class IFileStorageService(ABC):
    @abstractmethod
    async def save_file(self, filename: str, file_stream: BinaryIO) -> Path:
        """Сохраняет файл и возвращает путь к нему."""
        ...

    @abstractmethod
    async def delete_file(self, filename: str) -> bool:
        """Удаляет файл из локального хранилища. Возвращает True, если файл удален (или отсутствовал)."""
        ...

    @abstractmethod
    def get_download_url(self, filename: str) -> str:
        """Генерирует публичную ссылку для скачивания файла."""
        ...
