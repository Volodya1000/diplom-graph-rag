from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    TesseractCliOcrOptions,
    EasyOcrOptions,
    TableFormerMode
)

from src.config.parsing_settings import ParsingSettings, OcrEngineType



def build_pipeline_options(settings: ParsingSettings) -> PdfPipelineOptions:
    """
    Создает PdfPipelineOptions на основе переданных настроек.
    Здесь происходит магия переключения движков.
    """

    if settings.ocr_engine == OcrEngineType.TESSERACT:
        ocr_options = TesseractCliOcrOptions(
            force_full_page_ocr=False,
            lang=settings.tesseract_langs,
            tesseract_cmd=settings.tesseract_cmd
        )
    elif settings.ocr_engine == OcrEngineType.EASYOCR:
        ocr_options = EasyOcrOptions(
            force_full_page_ocr=False,
            lang=settings.easyocr_langs,
        )
    else:
        # Это скажет тайп-чекеру, что None сюда никогда не попадет
        raise ValueError(f"Неизвестный OCR движок: {settings.ocr_engine}")

    # 2. Настройка таблиц (общая для всех, но можно тоже вынести в if)
    table_options = TableStructureOptions(
        do_cell_matching=True,
        mode=TableFormerMode.ACCURATE
    )

    # 3. Сборка финального объекта
    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=ocr_options,
        do_table_structure=settings.do_table_structure,
        table_structure_options=table_options,
        images_scale=settings.images_scale,
        generate_page_images=settings.generate_page_images,
        generate_table_images=False
    )

    return pipeline_options