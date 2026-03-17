#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CLI для индексации PDF-документа в графовую БД
"""

import sys
from pathlib import Path

# Самое первое действие — добавляем корень проекта в sys.path
# Это нужно делать до любых импортов из src/
root = Path(__file__).resolve().parents[3]          # поднимаемся на 3 уровня вверх
sys.path.insert(0, str(root))

# Настраиваем логирование ПЕРЕД импортом любых тяжёлых библиотек
from src.utils.logging import setup_logging

import logging
# Вызываем настройку логов как можно раньше
setup_logging(level=logging.INFO, disable_verbose=True)

# Теперь можно безопасно импортировать всё остальное
import asyncio

from rich.console import Console

from src.di.container import setup_di
from src.application.use_cases.ingest_document import IngestDocumentUseCase

# Получаем логгер уже после настройки
logger = logging.getLogger(__name__)

console = Console()


async def main():
    if len(sys.argv) != 2:
        console.print("[red]Использование: python document_cli.py <path_to_pdf>[/red]")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        console.print(f"[red]Файл не найден: {file_path}[/red]")
        sys.exit(1)

    container = setup_di()
    try:
        console.print("[dim]Сборка зависимостей и загрузка моделей...[/dim]")
        use_case = await container.get(IngestDocumentUseCase)

        console.print(f"[bold yellow]Индексация документа:[/bold yellow] {file_path.name}")
        doc_id = await use_case.execute(file_path)

        console.print("[bold green]✔ Успех![/bold green] Документ сохранен в Neo4j.")
        console.print(f"ID: [cyan]{doc_id}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Ошибка:[/bold red] {str(e)}")
        logger.exception("Детали ошибки:")
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())