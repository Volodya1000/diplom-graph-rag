from pydantic import BaseModel
from enum import Enum

class OcrEngineType(str, Enum):
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"

class ParsingSettings(BaseModel):
    ocr_engine: OcrEngineType = OcrEngineType.EASYOCR # Изменено для работы "из коробки" без установки Tesseract exe
    tesseract_langs: list[str] = ["rus", "eng"]
    easyocr_langs: list[str] = ["ru", "en"]
    tesseract_cmd: str = ""
    do_table_structure: bool = True
    images_scale: float = 2.0
    generate_page_images: bool = False