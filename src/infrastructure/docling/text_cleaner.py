import re
import unicodedata


class TextCleaner:
    """
    Класс для очистки текста от артефактов OCR, восстановления целостности предложений
    и удаления мусора форм (подчеркивания, чекбоксы).
    """

    # --- 1. БАЗОВАЯ ОЧИСТКА ---
    _RE_HIDDEN = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060-\u206F\ufeff]")
    _RE_UNDERSCORES = re.compile(r"_{2,}")  # ____
    _RE_DASHES_SEQ = re.compile(r"-{3,}")  # ----
    _RE_DOTS_SEQ = re.compile(r"\.{3,}")  # .... (линии заполнения)
    # Удаляет чекбоксы вида [ ], [x], [v], а также мусор после них типа "Ба Да" если это явно артефакты
    _RE_CHECKBOX = re.compile(r"\[\s*[xXvV]?\s*\]")
    _RE_GARBAGE_LINES = re.compile(r"^\s*[-_=*.,;:/|]{3,}\s*$", re.MULTILINE)

    # --- 2. ИСПРАВЛЕНИЕ ПЕРЕНОСОВ (HYPHENATION) ---
    # Находит "слово- \n продолжение" и склеивает в "словопродолжение"
    # Пример: "антикоррупцион- \n ного" -> "антикоррупционного"
    _RE_HYPHENATED_WORD = re.compile(r"(?<=[а-яА-Яa-zA-Z])-\s*\n\s*(?=[а-яa-z])")

    # --- 3. СКЛЕИВАНИЕ РАЗОРВАННЫХ СТРОК (LINE MERGING) ---
    # Если строка заканчивается НЕ на знак препинания (.!?:;), а следующая начинается с маленькой буквы
    # или цифры (не заголовок), то это одно предложение.
    _RE_BROKEN_LINE = re.compile(r"(?<=[^.!?;:\n])\s*\n\s*(?=[а-яa-z0-9])")

    # --- 4. ОЧИСТКА СПИСКОВ И МУСОРА ---
    # Исправляет артефакты типа "2. 1.1." -> "1.1." (фантомная нумерация строк)
    _RE_PHANTOM_NUMBERS = re.compile(r"^\s*\d+\.\s+(?=\d+\.\d+)", re.MULTILINE)

    # Множественные пробелы и энтеры
    _RE_MULTI_SPACE = re.compile(r" +")
    _RE_MULTI_NEWLINE = re.compile(r"\n{3,}")

    @classmethod
    def clean(cls, text: str) -> str:
        if not text:
            return ""

        # 1. Unicode нормализация
        text = unicodedata.normalize("NFKC", text)
        text = cls._RE_HIDDEN.sub("", text)

        # 2. Удаление структурного мусора (черты, точки для подписи)
        text = cls._RE_UNDERSCORES.sub(" ", text)
        text = cls._RE_DASHES_SEQ.sub(" ", text)
        text = cls._RE_DOTS_SEQ.sub(" ", text)
        text = cls._RE_CHECKBOX.sub("", text)
        text = cls._RE_GARBAGE_LINES.sub("", text)

        # 3. Исправление переносов слов (дефис на конце строки)
        # Важно делать ДО склеивания строк
        text = cls._RE_HYPHENATED_WORD.sub("", text)

        # 4. Склеивание разорванных предложений
        # Заменяем перенос строки на пробел, если это середина предложения
        text = cls._RE_BROKEN_LINE.sub(" ", text)

        # 5. Специфические фиксы OCR
        # Убираем фантомные цифры перед пунктами (напр. "5. 2.1." -> "2.1.")
        text = cls._RE_PHANTOM_NUMBERS.sub("", text)

        # Убираем одиночные странные символы на отдельных строках (опционально)
        # text = re.sub(r"^\s*[\|/]\s*$", "", text, flags=re.MULTILINE)

        # 6. Финальная очистка пробелов
        text = text.replace("\t", " ")
        text = cls._RE_MULTI_SPACE.sub(" ", text)
        text = cls._RE_MULTI_NEWLINE.sub("\n\n", text)

        return text.strip()