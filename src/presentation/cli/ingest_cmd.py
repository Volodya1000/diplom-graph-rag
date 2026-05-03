"""CLI: индексация PDF-документа."""

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def register():
    """Вызывается при импорте — команда уже добавлена декоратором."""


from src.presentation.cli.app import app


@app.command("ingest")
def ingest_cmd(
    file: Path = typer.Argument(
        ...,
        help="Путь к PDF-файлу",
        exists=True,
        readable=True,
    ),
):
    """Индексация PDF-документа в графовую БД."""
    console.print(f"[bold yellow]📄 Индексация:[/bold yellow] {file.name}")
    asyncio.run(_run(file))


async def _run(file_path: Path):
    from src.application.use_cases.ingest_document import IngestDocumentUseCase
    from src.di.container import setup_di
    from src.domain.interfaces.services.file_storage_service import IFileStorageService

    container = setup_di()
    try:
        # 1. Получаем сервис хранения файлов
        file_storage = await container.get(IFileStorageService)

        console.print("[dim]💾 Копирование файла во внутреннее хранилище (data/uploads)...[/dim]")

        # 2. Открываем переданный пользователем файл и сохраняем его в uploads
        with open(file_path, "rb") as f:
            saved_path = await file_storage.save_file(file_path.name, f)

        # 3. Передаем в UseCase путь к НОВОМУ (сохраненному) файлу
        use_case = await container.get(IngestDocumentUseCase)
        doc_id = await use_case.execute(saved_path)

        console.print(
            f"[bold green]✔ Успех![/bold green] doc_id: [cyan]{doc_id}[/cyan]",
        )
    except Exception as e:
        console.print(f"[bold red]✖ Ошибка:[/bold red] {e}")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()
