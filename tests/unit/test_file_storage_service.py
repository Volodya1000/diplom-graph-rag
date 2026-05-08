import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.file_storage_service import LocalFileStorageService

pytestmark = pytest.mark.unit


@pytest.fixture
def file_storage(tmp_path: Path) -> LocalFileStorageService:
    # Мокаем конфиг, чтобы не инициализировать весь AppSettings
    mock_config = MagicMock()
    mock_config.api_base_url = "http://my-fastapi.local:8000/"

    service = LocalFileStorageService(mock_config)
    # Подменяем директорию на временную (из фикстуры pytest),
    # чтобы не мусорить в реальной data/uploads во время тестов
    service._upload_dir = tmp_path
    return service


class TestLocalFileStorageService:
    def test_get_download_url_generates_correct_link(self, file_storage):
        # Обычное имя
        url1 = file_storage.get_download_url("report.pdf")
        assert url1 == "http://my-fastapi.local:8000/uploads/report.pdf"

        # Имя с пробелами и кириллицей (должно быть URL-encoded)
        url2 = file_storage.get_download_url("Отчет 2024.pdf")
        assert url2 == "http://my-fastapi.local:8000/uploads/%D0%9E%D1%82%D1%87%D0%B5%D1%82%202024.pdf"

    def test_get_download_url_empty_filename_returns_empty(self, file_storage):
        assert file_storage.get_download_url("") == ""

    @pytest.mark.asyncio
    async def test_save_file_writes_data_correctly(self, file_storage, tmp_path):
        filename = "test_doc.txt"
        file_content = b"Hello, Knowledge Graph!"
        fake_file_stream = io.BytesIO(file_content)

        # Вызываем метод
        saved_path = await file_storage.save_file(filename, fake_file_stream)

        # Проверяем, что файл реально создался во временной директории
        assert saved_path.exists()
        assert saved_path.parent == tmp_path
        assert saved_path.name == filename

        # Проверяем содержимое
        with open(saved_path, "rb") as f:
            assert f.read() == file_content

    @pytest.mark.asyncio
    async def test_delete_file_removes_file(self, file_storage, tmp_path):
        filename = "to_delete.txt"
        file_path = tmp_path / filename
        file_path.write_text("dummy")

        result = await file_storage.delete_file(filename)

        assert result is True
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_missing_ok(self, file_storage):
        result = await file_storage.delete_file("ghost.txt")
        # Метод возвращает True, так как отсутствие файла считается успешным удалением
        assert result is True
