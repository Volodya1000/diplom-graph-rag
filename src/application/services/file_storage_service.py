import shutil
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from src.domain.interfaces.services.file_storage_service import IFileStorageService
from src.config.app_settings import AppSettings


class LocalFileStorageService(IFileStorageService):
    def __init__(self, config: AppSettings):
        self._base_url = config.api_base_url.rstrip("/")
        self._upload_dir = Path("data/uploads")
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, filename: str, file_stream: BinaryIO) -> Path:
        file_path = self._upload_dir / filename
        # Используем синхронный IO в отдельном потоке (можно оставить синхронно для KISS)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file_stream, buffer)
        return file_path

    def get_download_url(self, filename: str) -> str:
        if not filename:
            return ""
        # Кодируем имя файла для безопасного использования в URL
        safe_filename = quote(filename)
        return f"{self._base_url}/uploads/{safe_filename}"
