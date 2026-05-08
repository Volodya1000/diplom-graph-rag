import logging

from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.services.file_storage_service import IFileStorageService

logger = logging.getLogger(__name__)


class DeleteDocumentUseCase:
    def __init__(
        self,
        doc_repo: IDocumentRepository,
        file_storage: IFileStorageService,
    ):
        self.doc_repo = doc_repo
        self.file_storage = file_storage

    async def execute(self, filename: str) -> bool:
        logger.info(f"🗑️ Запуск удаления документа: {filename}")

        # 1. Удаляем из графа (Neo4j)
        db_deleted = await self.doc_repo.delete_document_by_filename(filename)

        if not db_deleted:
            logger.warning(f"⚠️ Документ '{filename}' не найден в базе графа знаний.")

        # 2. Удаляем из физического хранилища (даже если в БД нет, файл может быть "сиротой")
        file_deleted = await self.file_storage.delete_file(filename)

        if db_deleted or file_deleted:
            logger.info(f"✅ Успешное удаление: {filename} (БД: {db_deleted}, Файл: {file_deleted})")
            return True

        return False
