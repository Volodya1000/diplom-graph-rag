import shutil
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File
from dishka.integrations.fastapi import FromDishka, inject
from pydantic import BaseModel

from src.application.use_cases.ingest_document import IngestDocumentUseCase

router = APIRouter(prefix="/v1/documents", tags=["Documents"])


class IngestResponse(BaseModel):
    status: str
    message: str
    doc_id: str = ""


@router.post("/upload", response_model=IngestResponse)
@inject
async def upload_document(
    use_case: FromDishka[IngestDocumentUseCase], file: UploadFile = File(...)
):
    temp_dir = Path(tempfile.gettempdir()) / "graphrag_uploads"
    temp_dir.mkdir(exist_ok=True)
    filename = file.filename or "upload.pdf"
    file_path = temp_dir / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc_id = await use_case.execute(file_path)
        return IngestResponse(
            status="success", message="Document ingested successfully", doc_id=doc_id
        )
    except Exception as e:
        return IngestResponse(status="error", message=str(e))
    finally:
        if file_path.exists():
            file_path.unlink()
