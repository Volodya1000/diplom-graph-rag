"""CLI: индексация PDF-документа."""

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def register():
    """Вызывается при импорте — команда уже добавлена декоратором."""


from src.presentation.cli.app import app  # noqa: E402


@app.command("ingest")
def ingest_cmd(
    file: Path = typer.Argument(
        ...,
        help="Путь к PDF-файлу",
        exists=True,
        readable=True,
    ),
):
    """Индексация PDF-документа в графовую БД"""
    console.print(f"[bold yellow]📄 Индексация:[/bold yellow] {file.name}")
    asyncio.run(_run(file))


async def _run(file_path: Path):


    from src.di.container import setup_di
    from src.application.use_cases.ingest_document import IngestDocumentUseCase

    container = setup_di()
    try:
        use_case = await container.get(IngestDocumentUseCase)
        doc_id = await use_case.execute(file_path)
        console.print(
            f"[bold green]✔ Успех![/bold green] doc_id: [cyan]{doc_id}[/cyan]"
        )
    except Exception as e:
        console.print(f"[bold red]✖ Ошибка:[/bold red] {e}")
        logging.getLogger(__name__).exception("Детали:")
    finally:
        await container.close()
