from fastapi import APIRouter, UploadFile, File
from dishka.integrations.fastapi import FromDishka, inject
from pydantic import BaseModel

from src.application.use_cases.ingest_document import IngestDocumentUseCase
from src.domain.interfaces.services.file_storage_service import IFileStorageService  # <-- ДОБАВИТЬ ИМПОРТ

router = APIRouter(prefix="/v1/documents", tags=["Documents"])

class IngestResponse(BaseModel):
    status: str
    message: str
    doc_id: str = ""

@router.post("/upload", response_model=IngestResponse)
@inject
async def upload_document(
        # Сначала аргументы БЕЗ дефолтных значений (= ...)
        use_case: FromDishka[IngestDocumentUseCase],
        file_storage: FromDishka[IFileStorageService],
        # Потом аргументы С дефолтными значениями
        file: UploadFile = File(...)
):
    filename = file.filename or "upload.pdf"

    # 1. Сохраняем файл через Application Service
    file_path = await file_storage.save_file(filename, file.file)

    # 2. Передаем путь в UseCase для обработки
    try:
        doc_id = await use_case.execute(file_path)
        return IngestResponse(
            status="success", message="Document ingested successfully", doc_id=doc_id
        )
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        return IngestResponse(status="error", message=str(e))